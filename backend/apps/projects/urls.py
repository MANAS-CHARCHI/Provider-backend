from fastapi import APIRouter, Depends, Request, Form, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from . import views
from apps.users.decorators import login_required, role_required

router = APIRouter()

@router.post("/upload", response_model=dict)
@login_required
async def upload_project(name: str = Form(...), file: UploadFile = File(...), db: AsyncSession = Depends(get_db), request: Request = None):
    return await views.upload_project_view(name=name, file=file, db=db, request=request)

@router.put("/update/{project_id}", response_model=dict)
@login_required
async def update_project(project_id: int, file: UploadFile = File(...), db: AsyncSession = Depends(get_db), request: Request = None):
    return await views.update_project_view(db=db, request=request, project_id=project_id, file=file)


@router.delete("/delete/{project_id}", response_model=dict)
@login_required
async def delete_project(project_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    return await views.delete_project_view(project_id=project_id, db=db, request=request)


@router.get("/all", response_model=dict)
@login_required
async def get_all_projects(request: Request, db: AsyncSession = Depends(get_db)):
    return await views.get_all_project_view(db=db, request=request)


@router.get("/admin/user/{user_email}", response_model=dict)
@login_required
@role_required("admin")
async def get_user_project(user_email: str, request: Request, db: AsyncSession = Depends(get_db)):
    return await views.get_user_project_view(db=db, request=request, user_email=user_email)
