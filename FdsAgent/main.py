import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    port = int(os.getenv("FDS_PORT", "8002"))
    print(f"Starting FDS Agent Server on port {port}...")
    uvicorn.run("app.server:app", host="0.0.0.0", port=port, reload=False)
