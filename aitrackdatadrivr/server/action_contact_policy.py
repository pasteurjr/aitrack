"""Política determinística antiassédio, horário e orçamento de contatos."""

from dataclasses import dataclass
from datetime import datetime,time,timedelta,timezone
import hashlib
import json
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError


@dataclass(frozen=True)
class ContactPolicy:
    timezone_name:str
    quiet_start:time
    quiet_end:time
    max_attempts_per_incident:int
    max_contacts_per_target_day:int
    max_cost_cents_per_target_day:int
    cooldown_seconds:int
    max_consecutive_no_progress:int


@dataclass(frozen=True)
class ContactContext:
    attempt_count:int
    contacts_today:int
    cost_cents_today:int
    estimated_cost_cents:int
    last_contact_at:datetime|None
    consecutive_no_progress:int


def is_quiet_time(local_time,quiet_start,quiet_end):
    if quiet_start==quiet_end:return True
    if quiet_start<quiet_end:return quiet_start<=local_time<quiet_end
    return local_time>=quiet_start or local_time<quiet_end


def _database_time(value):
    """mysql-connector representa TIME como timedelta no MariaDB."""
    if isinstance(value,time):return value
    if isinstance(value,timedelta):
        seconds=int(value.total_seconds())%86400
        return time(seconds//3600,(seconds%3600)//60,seconds%60)
    raise ValueError('Horário da política inválido')


def evaluate_contact_policy(policy,context,now):
    if now.tzinfo is None:raise ValueError('now deve possuir fuso')
    try:zone=ZoneInfo(policy.timezone_name)
    except ZoneInfoNotFoundError as exc:raise ValueError('Timezone inválido') from exc
    local=now.astimezone(zone);reasons=[];next_allowed=None
    if is_quiet_time(local.timetz().replace(tzinfo=None),policy.quiet_start,policy.quiet_end):reasons.append('QUIET_HOURS')
    if context.attempt_count>=policy.max_attempts_per_incident:reasons.append('ATTEMPT_LIMIT')
    if context.contacts_today>=policy.max_contacts_per_target_day:reasons.append('DAILY_CONTACT_LIMIT')
    if context.cost_cents_today+context.estimated_cost_cents>policy.max_cost_cents_per_target_day:reasons.append('DAILY_COST_LIMIT')
    if context.last_contact_at:
        elapsed=(now-context.last_contact_at.astimezone(now.tzinfo)).total_seconds()
        if elapsed<policy.cooldown_seconds:reasons.append('COOLDOWN')
    if context.consecutive_no_progress>=policy.max_consecutive_no_progress:reasons.append('NO_PROGRESS_LIMIT')
    return {'allowed':not reasons,'denial_codes':reasons,'evaluated_local_at':local.replace(tzinfo=None),'next_allowed_at':next_allowed}


def enforce_contact_policy(connection,action,channel,estimated_cost_cents=0,now=None):
    if channel not in {'message','voice'} or not isinstance(estimated_cost_cents,int) or estimated_cost_cents<0:
        raise ValueError('Canal ou custo estimado inválido')
    now=now or datetime.now(timezone.utc);cursor=connection.cursor(dictionary=True)
    try:
        cursor.execute("""SELECT * FROM monitoramento.action_contact_policy_versions
          WHERE status='active' AND channel IN (%s,'all')
          ORDER BY channel=%s DESC,version_no DESC LIMIT 1""",(channel,channel));row=cursor.fetchone()
        if not row:raise PermissionError('Nenhuma política ativa para contato externo')
        zone=ZoneInfo(row['timezone_name']);local=now.astimezone(zone)
        start_local=datetime.combine(local.date(),time.min,tzinfo=zone);end_local=datetime.combine(local.date(),time.max,tzinfo=zone)
        start_utc=start_local.astimezone(timezone.utc).replace(tzinfo=None);end_utc=end_local.astimezone(timezone.utc).replace(tzinfo=None)
        target_hash=hashlib.sha256(action['target_ref'].encode()).hexdigest()
        cursor.execute("""SELECT COUNT(*) contacts,COALESCE(SUM(estimated_cost_cents),0) cost,
          MAX(created_at) last_contact FROM monitoramento.action_policy_decisions
          WHERE target_hash=%s AND allowed=TRUE AND created_at>=%s AND created_at<=%s""",(target_hash,start_utc,end_utc));usage=cursor.fetchone()
        cursor.execute("""SELECT status FROM monitoramento.action_queue WHERE incident_id=%s
          AND target_ref=%s AND action_type IN ('send_message','call_owner')
          AND id<>%s
          ORDER BY created_at DESC,id DESC LIMIT %s""",(
            action['incident_id'],action['target_ref'],action['id'],
            row['max_consecutive_no_progress'],
          ));statuses=[x['status'] for x in cursor.fetchall()]
        no_progress=0
        for status in statuses:
            if status=='responded':break
            no_progress+=1
        last=usage['last_contact']
        if last:last=last.replace(tzinfo=timezone.utc)
        policy=ContactPolicy(row['timezone_name'],_database_time(row['quiet_start']),_database_time(row['quiet_end']),row['max_attempts_per_incident'],row['max_contacts_per_target_day'],row['max_cost_cents_per_target_day'],row['cooldown_seconds'],row['max_consecutive_no_progress'])
        context=ContactContext(int(action['attempt_count']),int(usage['contacts']),int(usage['cost']),estimated_cost_cents,last,no_progress)
        result=evaluate_contact_policy(policy,context,now)
        bucket=local.strftime('%Y%m%d%H');evaluation_key=f'{action["public_id"]}:policy:{bucket}'
        snapshot={'attempt_count':context.attempt_count,'contacts_today':context.contacts_today,'cost_cents_today':context.cost_cents_today,'estimated_cost_cents':context.estimated_cost_cents,'consecutive_no_progress':context.consecutive_no_progress,'timezone':policy.timezone_name}
        cursor.execute("SELECT * FROM monitoramento.action_policy_decisions WHERE evaluation_key=%s",(evaluation_key,));existing=cursor.fetchone()
        if existing:return {'allowed':bool(existing['allowed']),'denial_codes':json.loads(existing['denial_codes_json']),'idempotent_replay':True}
        cursor.execute("""INSERT INTO monitoramento.action_policy_decisions
          (action_id,policy_version_id,evaluation_key,allowed,denial_codes_json,context_snapshot_json,target_hash,estimated_cost_cents,evaluated_local_at,next_allowed_at)
          VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",(action['id'],row['id'],evaluation_key,result['allowed'],json.dumps(result['denial_codes']),json.dumps(snapshot,separators=(',',':'),sort_keys=True),target_hash,estimated_cost_cents,result['evaluated_local_at'],result['next_allowed_at']))
        return {**result,'idempotent_replay':False}
    finally:cursor.close()
