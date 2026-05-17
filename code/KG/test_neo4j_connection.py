"""
Test script to diagnose Neo4j Aura connection issues
"""
import sys
import time
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError

def test_connection(uri, user, password, database):
    """Test basic Neo4j connection without running any Cypher"""
    print(f"Testing connection to: {uri}")
    print(f"User: {user}")
    print(f"Database: {database}")
    print("-" * 50)
    
    try:
        print("1. Creating driver...")
        driver = GraphDatabase.driver(uri, auth=(user, password))
        print("   ✓ Driver created successfully")
        
        print("2. Testing connectivity (verify_connectivity)...")
        driver.verify_connectivity()
        print("   ✓ Connectivity verified")
        
        print("3. Creating session...")
        session = driver.session(database=database)
        print("   ✓ Session created")
        
        print("4. Running simple query...")
        result = session.run("RETURN 1 as test")
        value = result.single()
        print(f"   ✓ Query successful: {value}")
        
        print("5. Checking database info...")
        result = session.run("CALL dbms.components() YIELD name, versions RETURN name, versions")
        for record in result:
            print(f"   - {record['name']}: {record['versions']}")
        
        session.close()
        driver.close()
        print("\n✓✓✓ All tests passed! Connection is working.")
        return True
        
    except AuthError as e:
        print(f"\n✗ Authentication Error: {e}")
        print("  Kiểm tra: username, password, URI có đúng không?")
        return False
        
    except ServiceUnavailable as e:
        print(f"\n✗ Service Unavailable Error: {e}")
        print("  Kiểm tra các điểm:")
        print("  1. Instance trên console.neo4j.io có status 'Running' không?")
        print("  2. Chờ thêm 30-60 giây và thử lại (instance có thể đang khởi tạo)")
        print("  3. Thử khởi động lại instance")
        print("  4. Kiểm tra firewall/network")
        return False
        
    except Exception as e:
        print(f"\n✗ Unexpected Error ({type(e).__name__}): {e}")
        print("  Chi tiết lỗi:")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Credentials from Neo4j.txt (updated 2026-05-13)
    uri = "neo4j+s://2e2fdb07.databases.neo4j.io"
    user = "2e2fdb07"
    password = "bKfubU3XukbxsGJ_6FzojFUWxTZ6EBk0I6lhbT7jLlc"
    database = "2e2fdb07"
    
    print("=" * 50)
    print("NEO4J AURA CONNECTION TEST")
    print("=" * 50)
    print()
    
    success = test_connection(uri, user, password, database)
    sys.exit(0 if success else 1)
