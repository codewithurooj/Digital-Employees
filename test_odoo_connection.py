"""Diagnose Odoo connection — try multiple database name patterns."""
import json
import xmlrpc.client

config = json.load(open('./config/odoo_config.json'))
url = config['url']
username = config['username']
api_key = config['api_key']

common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common", allow_none=True)

print(f"URL      : {url}")
print(f"Username : {username}")
print(f"Odoo     : {common.version()['server_version']}\n")

# Try common SaaS database name patterns
subdomain = url.replace("https://", "").replace(".odoo.com", "")
candidates = [
    subdomain,                          # autoflowai
    f"{subdomain}-main-0001",           # autoflowai-main-0001
    f"{subdomain}-master-0001",         # autoflowai-master-0001
    f"{subdomain}1",                    # autoflowai1
    f"{subdomain}-1",                   # autoflowai-1
]

import getpass
print("Enter your Odoo LOGIN PASSWORD (hidden, press Enter after typing):")
password = getpass.getpass("> ")
print()

print("Testing database name candidates with your login password:")
print("-" * 50)
found_db = None
for db in candidates:
    try:
        uid = common.authenticate(db, username, password, {})
        if uid:
            print(f"  SUCCESS: database = '{db}' (uid: {uid})")
            found_db = db
            break
        else:
            print(f"  FAILED : '{db}'")
    except Exception as e:
        print(f"  ERROR  : '{db}' -> {e}")

print()
if found_db:
    print(f"Found correct database: '{found_db}'")
    print(f"Update config/odoo_config.json: \"database\": \"{found_db}\"")
else:
    print("None of the common patterns worked.")
    print("Go to Odoo -> Settings -> General Settings -> find your database name")
    print("Then update config/odoo_config.json with the correct database name")
