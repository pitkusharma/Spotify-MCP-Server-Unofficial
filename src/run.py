import uvicorn
from src.core.config import settings
# from src.mcp_server import mcp

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
