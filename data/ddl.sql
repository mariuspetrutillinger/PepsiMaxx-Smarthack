
        CREATE TABLE team (
            id TEXT PRIMARY KEY,
            color TEXT,
            name TEXT NOT NULL,
            api_key TEXT NOT NULL,
            internal_use BOOLEAN NOT NULL
        );
        CREATE TABLE eval_session (
            id TEXT PRIMARY KEY,
            team_id TEXT NOT NULL,
            current_day INTEGER NOT NULL,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP,
            cost_value INTEGER NOT NULL,
            co2_value INTEGER NOT NULL,
            FOREIGN KEY (team_id) REFERENCES team (id)
        );
        CREATE TABLE network_node (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            capacity INTEGER,
            max_output INTEGER,
            max_input INTEGER,
            production INTEGER,
            overflow_penalty REAL,
            underflow_penalty REAL,
            over_output_penalty REAL,
            over_input_penalty REAL,
            production_cost REAL,
            production_co2 REAL,
            late_delivery_penalty REAL,
            early_delivery_penalty REAL,
            initial_stock INTEGER,
            node_type TEXT
        );
        CREATE TABLE network_connection (
            id TEXT PRIMARY KEY,
            from_id TEXT NOT NULL,
            to_id TEXT NOT NULL,
            distance INTEGER NOT NULL,
            lead_time_days INTEGER NOT NULL,
            connection_type TEXT NOT NULL,
            max_capacity INTEGER,
            FOREIGN KEY (from_id) REFERENCES network_node (id),
            FOREIGN KEY (to_id) REFERENCES network_node (id)
        );
        CREATE TABLE node_status (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            node_id TEXT NOT NULL,
            stock INTEGER,
            cost REAL NOT NULL,
            co2 REAL NOT NULL,
            FOREIGN KEY (session_id) REFERENCES eval_session (id),
            FOREIGN KEY (node_id) REFERENCES network_node (id)
        );
        CREATE TABLE requested_movement (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            connection_id TEXT NOT NULL,
            from_id TEXT NOT NULL,
            to_id TEXT NOT NULL,
            amount INTEGER NOT NULL,
            day_posted INTEGER NOT NULL,
            day_delivered INTEGER NOT NULL,
            cost REAL,
            co2 REAL,
            FOREIGN KEY (session_id) REFERENCES eval_session (id),
            FOREIGN KEY (connection_id) REFERENCES network_connection (id),
            FOREIGN KEY (from_id) REFERENCES node_status (id),
            FOREIGN KEY (to_id) REFERENCES node_status (id)
        );
        CREATE TABLE penalty (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            penalty_type TEXT,
            node_id TEXT,
            movement_id TEXT,
            co2 REAL,
            cost REAL,
            issued_day INTEGER NOT NULL,
            message TEXT,
            processed BOOLEAN NOT NULL,
            FOREIGN KEY (session_id) REFERENCES eval_session (id),
            FOREIGN KEY (node_id) REFERENCES network_node (id),
            FOREIGN KEY (movement_id) REFERENCES requested_movement (id)
        );
        CREATE TABLE demand (
            id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            post_day INTEGER NOT NULL,
            start_delivery_day INTEGER NOT NULL,
            end_delivery_day INTEGER NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES network_node (id)
        );
        CREATE TABLE demand_status (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            demand_id TEXT NOT NULL,
            node_status_id TEXT NOT NULL,
            remaining_quantity INTEGER,
            FOREIGN KEY (session_id) REFERENCES eval_session (id),
            FOREIGN KEY (demand_id) REFERENCES demand (id),
            FOREIGN KEY (node_status_id) REFERENCES node_status (id)
        );
        CREATE TABLE eval_track (
            id TEXT PRIMARY KEY,
            team_id TEXT NOT NULL,
            prod_Day INTEGER,
            production_Cost REAL,
            production_Co2 REAL,
            movement_Cost REAL,
            movement_Co2 REAL,
            penalty_Cost REAL,
            penalty_Co2 REAL,
            session_id TEXT,
            latest BOOLEAN DEFAULT FALSE,
            time_received TIMESTAMP,
            FOREIGN KEY (team_id) REFERENCES team (id)
        );