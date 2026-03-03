# 🧪 Relatório de Validação - API AITrack Monitor System

**Data:** 2026-03-02 17:11:47
**Total de Testes:** 21
**Passaram:** ✅ 0
**Falharam:** ❌ 21
**Taxa de Sucesso:** 0.0%

---

## 📊 Resumo por Categoria


### MONITORS
**Status:** 0/4 testes passaram

| Status | Método | Endpoint | Nome |
|--------|--------|----------|------|
| ❌ ERROR | `GET` | `/monitors` | Listar todos os monitores |
| ❌ ERROR | `GET` | `/monitors/1` | Buscar monitor #1 |
| ❌ ERROR | `GET` | `/monitors/999` | Buscar monitor inexistente |
| ❌ ERROR | `GET` | `/monitors/stats` | Estatísticas de monitores |

### VEHICLES
**Status:** 0/3 testes passaram

| Status | Método | Endpoint | Nome |
|--------|--------|----------|------|
| ❌ ERROR | `GET` | `/monitors/1/vehicles` | Listar veículos do monitor #1 |
| ❌ ERROR | `GET` | `/monitors/2/vehicles` | Listar veículos do monitor #2 |
| ❌ ERROR | `GET` | `/vehicles/SIM-1000/score` | Score do veículo SIM-1000 |

### ANALYSES
**Status:** 0/2 testes passaram

| Status | Método | Endpoint | Nome |
|--------|--------|----------|------|
| ❌ ERROR | `GET` | `/monitors/1/analyses` | Listar análises do monitor #1 |
| ❌ ERROR | `GET` | `/monitors/1/analyses?limit=10` | Listar análises com limite |

### ALERTS
**Status:** 0/5 testes passaram

| Status | Método | Endpoint | Nome |
|--------|--------|----------|------|
| ❌ ERROR | `GET` | `/alerts` | Listar todos os alertas |
| ❌ ERROR | `GET` | `/alerts?status=pending` | Listar alertas pendentes |
| ❌ ERROR | `GET` | `/alerts?severidade=critical` | Listar alertas críticos |
| ❌ ERROR | `GET` | `/alerts/stats` | Estatísticas de alertas |
| ❌ ERROR | `GET` | `/alerts` | Buscar alertas para teste |

### EVENTS
**Status:** 0/5 testes passaram

| Status | Método | Endpoint | Nome |
|--------|--------|----------|------|
| ❌ ERROR | `GET` | `/events/catalog` | Catálogo de tipos de eventos |
| ❌ ERROR | `GET` | `/events?limit=10` | Listar eventos (limite 10) |
| ❌ ERROR | `GET` | `/events?device_id=SIM-1000` | Listar eventos do SIM-1000 |
| ❌ ERROR | `GET` | `/events/stats` | Estatísticas de eventos |
| ❌ ERROR | `GET` | `/fleet/events?limit=20` | Eventos comportamentais |

### FLEET
**Status:** 0/2 testes passaram

| Status | Método | Endpoint | Nome |
|--------|--------|----------|------|
| ❌ ERROR | `GET` | `/fleet/scores` | Scores de todos os veículos |
| ❌ ERROR | `GET` | `/fleet/stats` | Estatísticas da frota |

---

## 📋 Detalhes dos Testes


### 1. Listar todos os monitores

**Método:** `GET`  
**Endpoint:** `/monitors`  
**Status:** ❌ ERROR  

**Erro:**
```
HTTPConnectionPool(host='localhost', port=5009): Max retries exceeded with url: /api/monitors (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x76bf62b24830>: Failed to establish a new connection: [Errno 111] Connection refused'))
```

### 2. Buscar monitor #1

**Método:** `GET`  
**Endpoint:** `/monitors/1`  
**Status:** ❌ ERROR  

**Erro:**
```
HTTPConnectionPool(host='localhost', port=5009): Max retries exceeded with url: /api/monitors/1 (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x76bf62b2ccd0>: Failed to establish a new connection: [Errno 111] Connection refused'))
```

### 3. Buscar monitor inexistente

**Método:** `GET`  
**Endpoint:** `/monitors/999`  
**Status:** ❌ ERROR  

**Erro:**
```
HTTPConnectionPool(host='localhost', port=5009): Max retries exceeded with url: /api/monitors/999 (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x76bf62b2d6d0>: Failed to establish a new connection: [Errno 111] Connection refused'))
```

### 4. Estatísticas de monitores

**Método:** `GET`  
**Endpoint:** `/monitors/stats`  
**Status:** ❌ ERROR  

**Erro:**
```
HTTPConnectionPool(host='localhost', port=5009): Max retries exceeded with url: /api/monitors/stats (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x76bf62b315b0>: Failed to establish a new connection: [Errno 111] Connection refused'))
```

### 5. Listar veículos do monitor #1

**Método:** `GET`  
**Endpoint:** `/monitors/1/vehicles`  
**Status:** ❌ ERROR  

**Erro:**
```
HTTPConnectionPool(host='localhost', port=5009): Max retries exceeded with url: /api/monitors/1/vehicles (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x76bf62b31cd0>: Failed to establish a new connection: [Errno 111] Connection refused'))
```

### 6. Listar veículos do monitor #2

**Método:** `GET`  
**Endpoint:** `/monitors/2/vehicles`  
**Status:** ❌ ERROR  

**Erro:**
```
HTTPConnectionPool(host='localhost', port=5009): Max retries exceeded with url: /api/monitors/2/vehicles (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x76bf62b345f0>: Failed to establish a new connection: [Errno 111] Connection refused'))
```

### 7. Listar análises do monitor #1

**Método:** `GET`  
**Endpoint:** `/monitors/1/analyses`  
**Status:** ❌ ERROR  

**Erro:**
```
HTTPConnectionPool(host='localhost', port=5009): Max retries exceeded with url: /api/monitors/1/analyses (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x76bf62ad2470>: Failed to establish a new connection: [Errno 111] Connection refused'))
```

### 8. Listar análises com limite

**Método:** `GET`  
**Endpoint:** `/monitors/1/analyses?limit=10`  
**Status:** ❌ ERROR  

**Erro:**
```
HTTPConnectionPool(host='localhost', port=5009): Max retries exceeded with url: /api/monitors/1/analyses?limit=10 (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x76bf62ad1ae0>: Failed to establish a new connection: [Errno 111] Connection refused'))
```

### 9. Listar todos os alertas

**Método:** `GET`  
**Endpoint:** `/alerts`  
**Status:** ❌ ERROR  

**Erro:**
```
HTTPConnectionPool(host='localhost', port=5009): Max retries exceeded with url: /api/alerts (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x76bf62ad1bf0>: Failed to establish a new connection: [Errno 111] Connection refused'))
```

### 10. Listar alertas pendentes

**Método:** `GET`  
**Endpoint:** `/alerts?status=pending`  
**Status:** ❌ ERROR  

**Erro:**
```
HTTPConnectionPool(host='localhost', port=5009): Max retries exceeded with url: /api/alerts?status=pending (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x76bf62ad18c0>: Failed to establish a new connection: [Errno 111] Connection refused'))
```

### 11. Listar alertas críticos

**Método:** `GET`  
**Endpoint:** `/alerts?severidade=critical`  
**Status:** ❌ ERROR  

**Erro:**
```
HTTPConnectionPool(host='localhost', port=5009): Max retries exceeded with url: /api/alerts?severidade=critical (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x76bf62ad07c0>: Failed to establish a new connection: [Errno 111] Connection refused'))
```

### 12. Estatísticas de alertas

**Método:** `GET`  
**Endpoint:** `/alerts/stats`  
**Status:** ❌ ERROR  

**Erro:**
```
HTTPConnectionPool(host='localhost', port=5009): Max retries exceeded with url: /api/alerts/stats (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x76bf62ad2cf0>: Failed to establish a new connection: [Errno 111] Connection refused'))
```

### 13. Buscar alertas para teste

**Método:** `GET`  
**Endpoint:** `/alerts`  
**Status:** ❌ ERROR  

**Erro:**
```
HTTPConnectionPool(host='localhost', port=5009): Max retries exceeded with url: /api/alerts (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x76bf62ad2f10>: Failed to establish a new connection: [Errno 111] Connection refused'))
```

### 14. Catálogo de tipos de eventos

**Método:** `GET`  
**Endpoint:** `/events/catalog`  
**Status:** ❌ ERROR  

**Erro:**
```
HTTPConnectionPool(host='localhost', port=5009): Max retries exceeded with url: /api/events/catalog (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x76bf62ad3130>: Failed to establish a new connection: [Errno 111] Connection refused'))
```

### 15. Listar eventos (limite 10)

**Método:** `GET`  
**Endpoint:** `/events?limit=10`  
**Status:** ❌ ERROR  

**Erro:**
```
HTTPConnectionPool(host='localhost', port=5009): Max retries exceeded with url: /api/events?limit=10 (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x76bf62ad3350>: Failed to establish a new connection: [Errno 111] Connection refused'))
```

### 16. Listar eventos do SIM-1000

**Método:** `GET`  
**Endpoint:** `/events?device_id=SIM-1000`  
**Status:** ❌ ERROR  

**Erro:**
```
HTTPConnectionPool(host='localhost', port=5009): Max retries exceeded with url: /api/events?device_id=SIM-1000 (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x76bf62ad3570>: Failed to establish a new connection: [Errno 111] Connection refused'))
```

### 17. Estatísticas de eventos

**Método:** `GET`  
**Endpoint:** `/events/stats`  
**Status:** ❌ ERROR  

**Erro:**
```
HTTPConnectionPool(host='localhost', port=5009): Max retries exceeded with url: /api/events/stats (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x76bf62ad3790>: Failed to establish a new connection: [Errno 111] Connection refused'))
```

### 18. Scores de todos os veículos

**Método:** `GET`  
**Endpoint:** `/fleet/scores`  
**Status:** ❌ ERROR  

**Erro:**
```
HTTPConnectionPool(host='localhost', port=5009): Max retries exceeded with url: /api/fleet/scores (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x76bf62ad39b0>: Failed to establish a new connection: [Errno 111] Connection refused'))
```

### 19. Eventos comportamentais

**Método:** `GET`  
**Endpoint:** `/fleet/events?limit=20`  
**Status:** ❌ ERROR  

**Erro:**
```
HTTPConnectionPool(host='localhost', port=5009): Max retries exceeded with url: /api/fleet/events?limit=20 (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x76bf62ad3bd0>: Failed to establish a new connection: [Errno 111] Connection refused'))
```

### 20. Estatísticas da frota

**Método:** `GET`  
**Endpoint:** `/fleet/stats`  
**Status:** ❌ ERROR  

**Erro:**
```
HTTPConnectionPool(host='localhost', port=5009): Max retries exceeded with url: /api/fleet/stats (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x76bf62ad3df0>: Failed to establish a new connection: [Errno 111] Connection refused'))
```

### 21. Score do veículo SIM-1000

**Método:** `GET`  
**Endpoint:** `/vehicles/SIM-1000/score`  
**Status:** ❌ ERROR  

**Erro:**
```
HTTPConnectionPool(host='localhost', port=5009): Max retries exceeded with url: /api/vehicles/SIM-1000/score (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x76bf62ad3bd0>: Failed to establish a new connection: [Errno 111] Connection refused'))
```

---

## 📊 Estatísticas Finais

- **Total de Endpoints Testados:** 21
- **Sucessos:** ✅ 0
- **Falhas:** ❌ 21
- **Taxa de Sucesso:** 0.0%

### ⚠️ 21 teste(s) falharam

Verifique os detalhes acima para identificar e corrigir os problemas.

---

*Relatório gerado automaticamente em 2026-03-02 17:11:47*
