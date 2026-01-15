def create_ocr_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ocr_extractions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            filename VARCHAR(255),
            document_type VARCHAR(50),
            name VARCHAR(255),
            email VARCHAR(255),
            phone VARCHAR(50),
            aadhaar VARCHAR(20),
            pan VARCHAR(20),
            address TEXT,
            state VARCHAR(100),
            country VARCHAR(100),
            raw_text TEXT,
            confidence_score FLOAT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)