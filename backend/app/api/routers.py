from fastapi import APIRouter
router=APIRouter()


@router.get("/health")
async def health_check():
    return {
        "status":"healthy",
        "message":"the api is working"
    }
@router.get("/info")
async def get_app_info():
    return {
        "name":"clipped-ai",
        "description":"short form ugc content automation",
        "version":"2.0"
    }
