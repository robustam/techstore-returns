# Diagrama de orquestación — TechStore Returns

```mermaid
flowchart TD
    U([Usuario / Streamlit]) --> PS[procesar_solicitud]
    PS --> CP[consultar_pedido<br/>incluye historical]
    CP --> VP[validar_politica<br/>30 días]
    VP --> CE[construir_estado]
    CE --> PL{{Planner<br/>decidir_accion<br/>6 reglas priorizadas}}

    PL -->|R1: fuera de plazo| ESC[escalar]
    PL -->|R2: monto > $100.000| SAP[solicitar_aprobacion]
    PL -->|R3: >= 3 devol. 90d| ESCF[escalar_fraude]
    PL -->|R4: recurrente < $50.000| APR[aprobar_preferente]
    PL -->|R5: sin comprobante/desc| SI[solicitar_info]
    PL -->|R6: caso estándar| APE[aprobar_estandar]

    APR --> CR[calcular_reembolso]
    APE --> CR
    CR --> GE[generar_etiqueta]
    GE --> AC1[actualizar_crm]
    AC1 --> NC1[notificar_cliente]

    ESC --> AC2[actualizar_crm]
    ESCF --> AC2
    SAP --> AC2
    AC2 --> NC2[notificar_cliente]

    SI --> NC3[notificar_cliente]

    NC1 --> GD[guardar_decision<br/>memoria largo plazo]
    NC2 --> GD
    NC3 --> GD
    GD --> R([Respuesta + traza en UI])

    %% Rama LLM abierta
    U -.preguntas abiertas.-> AE[AgentExecutor<br/>Gemini Flash]
    AE -.elige entre 7 tools.-> TOOLS[(7 tools)]
    CP -.-> TOOLS
    VP -.-> TOOLS
    CR -.-> TOOLS
    GE -.-> TOOLS
    AC1 -.-> TOOLS
    NC1 -.-> TOOLS
    BCS -.-> TOOLS
    BCS[buscar_casos_similares<br/>Chroma RAG]

    %% Estilos
    classDef riesgo fill:#ffe0e0,stroke:#c0392b,color:#000
    classDef amable fill:#e0f7e0,stroke:#27ae60,color:#000
    classDef info fill:#e0f0ff,stroke:#2980b9,color:#000
    class ESC,ESCF,SAP riesgo
    class APR,APE amable
    class SI info