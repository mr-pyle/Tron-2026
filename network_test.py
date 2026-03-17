import socket

def run_server():
    port = 5050
    # Try to automatically find this computer's IP address
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 0.0.0.0 means "listen on all network adapters"
    server.bind(('0.0.0.0', port))
    server.listen(1)
    
    print("\n" + "="*40)
    print(" 🖥️  TEACHER SERVER RUNNING")
    print("="*40)
    print(f"Tell the student PC to connect to this IP: {local_ip}")
    print(f"Listening on port {port}...")
    print("Waiting for a student to connect...\n")
    
    try:
        client_socket, addr = server.accept()
        print(f"✅ SUCCESS! Connection received from {addr[0]}")
        data = client_socket.recv(1024).decode('utf-8')
        print(f"📩 Message from student: '{data}'")
        client_socket.close()
    except Exception as e:
        print(f"❌ Server Error: {e}")
    finally:
        server.close()

def run_client():
    print("\n" + "="*40)
    print(" 💻  STUDENT CLIENT RUNNING")
    print("="*40)
    server_ip = input("Enter the Teacher's IP address: ").strip()
    port = 5050
    
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(5.0) # Don't wait forever if it's blocked
        
        print(f"\nAttempting to connect to {server_ip}:{port}...")
        client.connect((server_ip, port))
        
        client.send("Hello from the student PC! The network is open!".encode('utf-8'))
        print("✅ SUCCESS! Message sent to the teacher's computer.")
        client.close()
        
    except TimeoutError:
        print("\n❌ FAILED: Connection timed out.")
        print("This usually means the Teacher's Windows Firewall is blocking incoming connections on port 5050.")
    except ConnectionRefusedError:
        print("\n❌ FAILED: Connection refused.")
        print("This usually means the Teacher's IP is wrong, or the Server script isn't running yet.")
    except Exception as e:
        print(f"\n❌ FAILED: {e}")

if __name__ == "__main__":
    print("--- TRON NETWORK TEST ---")
    print("1. Teacher (Run Server)")
    print("2. Student (Run Client)")
    choice = input("Choose mode (1 or 2): ").strip()
    
    if choice == '1':
        run_server()
    elif choice == '2':
        run_client()
    else:
        print("Invalid choice. Exiting.")
    
    input("\nPress Enter to close...")