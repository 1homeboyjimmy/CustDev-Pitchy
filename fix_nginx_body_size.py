import paramiko

# Server configurations from fix_nginx.py
servers = [
    ('193.187.94.144', 'rWNlaWDxT}VL{TlQh5x*f|0Aqf0xI3rf'),
    ('141.105.71.21', '4KUpHgm3_f')
]

def fix_server(ip, pw):
    print(f"Connecting to {ip}...")
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, username='root', password=pw, timeout=10)
        
        nginx_config_path = '/etc/nginx/sites-available/custdev'
        
        print(f"  Checking {nginx_config_path} for client_max_body_size...")
        
        # Check if client_max_body_size already exists
        stdin, stdout, stderr = client.exec_command(f"grep 'client_max_body_size' {nginx_config_path}")
        exists = stdout.read().decode().strip()
        
        if exists:
            print("  Updating existing client_max_body_size to 100M...")
            command = f"sed -i 's/client_max_body_size [^;]*;/client_max_body_size 100M;/' {nginx_config_path}"
        else:
            print("  Adding client_max_body_size 100M to server block...")
            # Insert after 'server {' line
            command = f"sed -i '/server {{/a \\    client_max_body_size 100M;' {nginx_config_path}"
        
        stdin, stdout, stderr = client.exec_command(command)
        err = stderr.read().decode()
        if err: 
            print(f"  sed err: {err}")
            return
            
        print("  Testing Nginx configuration...")
        stdin, stdout, stderr = client.exec_command("nginx -t")
        t_out = stdout.read().decode()
        t_err = stderr.read().decode()
        
        if "test is successful" in t_err or "test is successful" in t_out:
            print("  Reloading Nginx...")
            client.exec_command("systemctl reload nginx")
            print(f"  Successfully updated Nginx on {ip}")
        else:
            print(f"  Nginx test failed on {ip}: {t_err}")
            
        client.close()
    except Exception as e:
        print(f"Failed for {ip}: {e}")

if __name__ == "__main__":
    for ip, pw in servers:
        fix_server(ip, pw)
    print("\nAll servers processed.")
