import uvicorn
from config.env import AppConfig_


if __name__ == '__main__':
    uvicorn.run(
        'app:app',
        host=AppConfig_.app_host,
        port=AppConfig_.app_port,
        reload=AppConfig_.app_debug,
    )