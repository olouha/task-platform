flowchart TB
    subgraph 数据源["数据来源"]
        A["我的钢铁网<br/>(mysteel.com)"]
    end

    subgraph 抓取层["价格抓取层"]
        B["定时任务调度<br/>(Scheduler)"]
        C["Playwright自动化<br/>(浏览器抓取)"]
        D["登录认证<br/>(Cookie管理)"]
        E["数据提取<br/>(表格解析)"]
    end

    subgraph 存储层["数据存储层"]
        F["SQLite数据库<br/>(yantai_rebar.db)"]
        G["Excel备份<br/>(历史数据)"]
        H["截图存档<br/>(网页快照)"]
    end

    subgraph API层["API服务层"]
        I["FastAPI后端"]
        J["WebSocket推送"]
        K["多业务模块"]
    end

    subgraph 前端层["前端展示层"]
        L["React前端"]
        M["价格监控页面<br/>(PriceMonitor)"]
        N["价格趋势图<br/>(Recharts)"]
        O["调差计算页面<br/>(Adjustment)"]
    end

    subgraph 调差计算["调差计算引擎"]
        P["配置规则<br/>(RuleConfig)"]
        Q["基准价获取"]
        R["施工期均价"]
        S["风险幅度判断"]
        T["调差公式计算"]
        U["结果输出"]
    end

    subgraph 调差规则["5种调差公式"]
        V["标准三段式"]
        W["无风险幅度"]
        X["比例调差法"]
        Y["造价信息调整法"]
        Z["龙湖增值税率换算"]
    end

    %% 数据抓取流程
    B -->|"定时触发/手动"| C
    A -->|"访问"| C
    C -->|"登录"| D
    D -->|"提取数据"| E
    E -->|"保存"| F
    E -->|"备份"| G
    E -->|"截图"| H

    %% API流程
    F -->|"查询"| I
    G -->|"读取"| I
    I -->|"实时推送"| J
    J -->|"WebSocket"| L
    I -->|"HTTP API"| L

    %% 前端展示
    L --> M
    L --> N
    L --> O

    %% 调差计算流程
    P --> Q
    Q --> R
    R --> S
    S --> T
    T --> U

    T -->|"选择公式"| V
    T -->|"选择公式"| W
    T -->|"选择公式"| X
    T -->|"选择公式"| Y
    T -->|"选择公式"| Z

    %% 6步计算流程标注
    style P fill:#e1f5ff,stroke:#01579b
    style Q fill:#e1f5ff,stroke:#01579b
    style R fill:#e1f5ff,stroke:#01579b
    style S fill:#e1f5ff,stroke:#01579b
    style T fill:#e1f5ff,stroke:#01579b
    style U fill:#e1f5ff,stroke:#01579b

    %% 数据源样式
    style A fill:#fff3e0,stroke:#e65100

    %% 抓取层样式
    style B fill:#f3e5f5,stroke:#7b1fa2
    style C fill:#f3e5f5,stroke:#7b1fa2
    style D fill:#f3e5f5,stroke:#7b1fa2
    style E fill:#f3e5f5,stroke:#7b1fa2

    %% 存储层样式
    style F fill:#e8f5e9,stroke:#2e7d32
    style G fill:#e8f5e9,stroke:#2e7d32
    style H fill:#e8f5e9,stroke:#2e7d32

    %% API层样式
    style I fill:#fce4ec,stroke:#c2185b
    style J fill:#fce4ec,stroke:#c2185b
    style K fill:#fce4ec,stroke:#c2185b

    %% 前端层样式
    style L fill:#fff8e1,stroke:#f9a825
    style M fill:#fff8e1,stroke:#f9a825
    style N fill:#fff8e1,stroke:#f9a825
    style O fill:#fff8e1,stroke:#f9a825

    %% 调差规则样式
    style V fill:#fce4ec,stroke:#ad1457
    style W fill:#fce4ec,stroke:#ad1457
    style X fill:#fce4ec,stroke:#ad1457
    style Y fill:#fce4ec,stroke:#ad1457
    style Z fill:#fce4ec,stroke:#ad1457
