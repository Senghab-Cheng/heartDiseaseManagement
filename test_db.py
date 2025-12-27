#!/usr/bin/env python3
import sys
sys.path.append('.')

try:
    from utils.database import init_db, get_connection
    print("Database imports OK")
    
    init_db()
    print("Database initialized")
    
    conn = get_connection()
    print(f"Connection type: {type(conn)}")
    conn.close()
    print("Connection closed")
    
    print("All database functions working!")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()