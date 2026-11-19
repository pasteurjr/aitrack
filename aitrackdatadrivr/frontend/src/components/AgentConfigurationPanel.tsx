import React, { FormEvent, useEffect, useState } from 'react';
import { agentConfigurationService } from '../services/apiService';
import type { AgentConfiguration, AgentDefinition, AutonomyLevel, AutonomousRisk } from '../types/agent';
import AsyncDataState from './AsyncDataState';

const externalActions = ['monitor','notify_operator','contact_owner','send_message','call_owner'];

export default function AgentConfigurationPanel() {
  const [agents,setAgents]=useState<AgentDefinition[]>([]);const [configs,setConfigs]=useState<AgentConfiguration[]>([]);
  const [tools,setTools]=useState<string[]>([]);const [selectedTools,setSelectedTools]=useState<string[]>([]);
  const [loading,setLoading]=useState(true);const [error,setError]=useState('');const [saving,setSaving]=useState(false);
  const [message,setMessage]=useState('');const [agentKey,setAgentKey]=useState('');
  const [objective,setObjective]=useState('');const [instructions,setInstructions]=useState('');
  const [provider,setProvider]=useState('');const [model,setModel]=useState('');const [actor,setActor]=useState('');const [reason,setReason]=useState('');
  const [timeout,setTimeoutValue]=useState(30);const [contextLimit,setContextLimit]=useState(100);const [actionLimit,setActionLimit]=useState(0);
  const [autonomy,setAutonomy]=useState<AutonomyLevel>('observe');const [risk,setRisk]=useState<AutonomousRisk>('none');const [actions,setActions]=useState<string[]>([]);

  const load=async()=>{setLoading(true);setError('');try{const [a,c,t]=await Promise.all([agentConfigurationService.getAgents(),agentConfigurationService.getConfigurations(),agentConfigurationService.getTools()]);setAgents(a.data.agents);setConfigs(c.data.configurations);setTools(t.data.tools);setAgentKey(value=>value||a.data.agents[0]?.agent_key||'');}catch{setError('Não foi possível carregar configurações reais dos agentes.');}finally{setLoading(false)}};
  useEffect(()=>{load()},[]);

  const toggle=(value:string,current:string[],set:(v:string[])=>void)=>set(current.includes(value)?current.filter(item=>item!==value):[...current,value]);
  const submit=async(event:FormEvent)=>{event.preventDefault();setSaving(true);setError('');setMessage('');try{
    const created=await agentConfigurationService.create({agent_key:agentKey,objective,instructions,provider_code:provider,model_code:model,decision_policy:{temperature:0,require_evidence:true},limits:{timeout_seconds:timeout,max_context_events:contextLimit,max_actions_per_run:actionLimit},created_by:actor,change_reason:reason});
    const id=created.data.id as number;
    for(const tool of selectedTools){await agentConfigurationService.addTool(id,{tool_name:tool,constraints:{allowed_arguments:tool==='vehicle.get'||tool==='position.latest'?['vehicle_id']:['vehicle_id','limit'],allowed_sources:['tracker','dirijabem'],max_limit:tool==='vehicle.get'||tool==='position.latest'?1:contextLimit},actor,reason});}
    await agentConfigurationService.addAutonomy(id,{policy:{autonomy_level:autonomy,execution_mode:'simulation',max_autonomous_risk:autonomy==='execute'?risk:'none',allowed_autonomous_actions:autonomy==='execute'?actions:[]},actor,reason});
    setMessage(`Versão ${created.data.version_number} criada como draft. Revise e ative separadamente.`);await load();
  }catch(err:any){setError(err?.response?.data?.error||'Falha ao criar a versão. O draft permanece inativo para correção.');}finally{setSaving(false)}};
  const activate=async(config:AgentConfiguration)=>{setSaving(true);setError('');try{await agentConfigurationService.activate(config.id,{actor,reason});setMessage(`Versão ${config.version_number} ativada.`);await load();}catch(err:any){setError(err?.response?.data?.error||'Não foi possível ativar a versão.');}finally{setSaving(false)}};

  if(loading)return <AsyncDataState variant="loading" message="Carregando agentes..."/>;
  if(error&&!agents.length)return <AsyncDataState variant="error" message={error} onRetry={load}/>;
  return <div style={s.page}><section style={s.form}><h2>Configurar agente de IA</h2><p style={s.note}>Toda alteração cria uma versão draft imutável. Nenhum modelo é chamado nesta tela.</p>{error&&<div role="alert" style={s.error}>{error}</div>}{message&&<div role="status" style={s.ok}>{message}</div>}
    <form onSubmit={submit}><div role="status" style={s.note}>Modo desta versão: SIMULAÇÃO — ações serão registradas, nunca enviadas.</div><label>Agente<select value={agentKey} onChange={e=>setAgentKey(e.target.value)} required>{agents.map(a=><option key={a.id} value={a.agent_key}>{a.display_name} ({a.agent_key})</option>)}</select></label>
    <label>Objetivo<textarea value={objective} onChange={e=>setObjective(e.target.value)} minLength={10} required/></label><label>Instruções<textarea value={instructions} onChange={e=>setInstructions(e.target.value)} minLength={20} required/></label>
    <div style={s.grid}><label>Provedor<input value={provider} onChange={e=>setProvider(e.target.value)} placeholder="anthropic ou openai" required/></label><label>Modelo<input value={model} onChange={e=>setModel(e.target.value)} required/></label><label>Timeout (s)<input type="number" min="1" max="300" value={timeout} onChange={e=>setTimeoutValue(Number(e.target.value))}/></label><label>Eventos de contexto<input type="number" min="1" max="500" value={contextLimit} onChange={e=>setContextLimit(Number(e.target.value))}/></label><label>Ações por execução<input type="number" min="0" max="20" value={actionLimit} onChange={e=>setActionLimit(Number(e.target.value))}/></label></div>
    <fieldset><legend>Ferramentas somente leitura</legend>{tools.map(t=><label key={t} style={s.check}><input type="checkbox" checked={selectedTools.includes(t)} onChange={()=>toggle(t,selectedTools,setSelectedTools)}/>{t}</label>)}</fieldset>
    <div style={s.grid}><label>Autonomia<select value={autonomy} onChange={e=>{const v=e.target.value as AutonomyLevel;setAutonomy(v);if(v!=='execute'){setRisk('none');setActions([])}else if(risk==='none'){setRisk('low')}}}><option value="observe">Observar</option><option value="recommend">Recomendar</option><option value="approval">Solicitar aprovação</option><option value="execute">Elegível para executar</option></select></label>{autonomy==='execute'&&<label>Risco autônomo máximo<select value={risk} onChange={e=>setRisk(e.target.value as AutonomousRisk)}><option value="low">Baixo</option><option value="medium">Médio</option></select></label>}</div>
    {autonomy==='execute'&&<fieldset><legend>Ações elegíveis (o canal revalidará)</legend>{externalActions.map(a=><label key={a} style={s.check}><input type="checkbox" checked={actions.includes(a)} onChange={()=>toggle(a,actions,setActions)}/>{a}</label>)}</fieldset>}
    <div style={s.grid}><label>Operador<input value={actor} onChange={e=>setActor(e.target.value)} required/></label><label>Motivo da mudança<input value={reason} onChange={e=>setReason(e.target.value)} minLength={5} required/></label></div><button disabled={saving||(autonomy==='execute'&&(risk==='none'||!actions.length||actionLimit<1))}>{saving?'Salvando...':'Criar versão draft'}</button></form></section>
    <section style={s.versions}><h2>Versões persistidas</h2>{configs.length===0?<AsyncDataState variant="empty" message="Nenhuma configuração foi criada."/>:configs.map(c=><article key={c.id} style={s.card}><strong>{c.display_name} · v{c.version_number}</strong><span style={s.badge}>{c.status}</span><p>{c.objective}</p><small>{c.provider_code} / {c.model_code} · {c.tool_policies.length} tools · {c.autonomy_policy?.autonomy_level||'autonomia pendente'}</small>{c.status==='draft'&&c.autonomy_policy&&<button disabled={saving||!actor||reason.length<5} onClick={()=>activate(c)}>Ativar esta versão</button>}</article>)}</section></div>;
}

const s:Record<string,React.CSSProperties>={page:{height:'100%',overflow:'auto',background:'#0f172a',color:'#e2e8f0',padding:20,display:'grid',gridTemplateColumns:'minmax(420px,1.2fr) minmax(320px,.8fr)',gap:20},form:{background:'#1e293b',padding:18,borderRadius:8},versions:{background:'#111827',padding:18,borderRadius:8},grid:{display:'grid',gridTemplateColumns:'repeat(2,minmax(0,1fr))',gap:10},note:{color:'#93c5fd'},error:{background:'#7f1d1d',padding:10},ok:{background:'#065f46',padding:10},check:{display:'inline-flex',gap:6,marginRight:14},card:{border:'1px solid #475569',borderRadius:6,padding:12,marginBottom:10},badge:{marginLeft:8,padding:'2px 6px',background:'#334155',borderRadius:4}};
