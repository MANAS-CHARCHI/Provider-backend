from fastapi import HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from apps.projects.models import Project
from apps.users.models import Users, Activity
from apps.projects.services.s3 import s3
import zipfile
import os
import shutil
import tempfile

def find_index_root(base_path: str) -> str:
    """
    Returns the directory path that contains index.html
    Raises error if none or multiple found
    """
    matches = []

    for root, _, files in os.walk(base_path):
        if "index.html" in files:
            matches.append(root)

    if not matches:
        raise HTTPException(status_code=400, detail="index.html not found")

    if len(matches) > 1:
        raise HTTPException(
            status_code=400,
            detail="Multiple index.html files found, ambiguous structure"
        )

    return matches[0]
MAX_FILE_SIZE = int(eval(os.getenv("MAX_FILE_SIZE", '20 * 1024 * 1024')))
async def upload_project_view(name: str, file: UploadFile, db: AsyncSession, request: Request):
    is_index = file.filename == "index.html"
    is_zip = file.filename.endswith(".zip")
    content = await file.read()
    file_size = len(content)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413, # Payload Too Large
            detail="File size exceeds the 20MB limit."
        )
    await file.seek(0)
    if not (is_index or is_zip):
        raise HTTPException(
            status_code=400,
            detail="Only index.html or ZIP files containing index.html are allowed"
        )
    
    result = await db.execute(
        select(Project).where(Project.name == name, Project.owner_id == request.state.user_id)
    )
    existing_project = result.scalar_one_or_none()
    if existing_project:
        raise HTTPException(status_code=400, detail="Project with this name already exists")

    # Create project in DB
    new_project = Project(
        name=name,
        owner_id=request.state.user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)

    # Temp dir
    temp_dir = tempfile.mkdtemp()
    try:
        if is_index:
            s3_key = f"projects/{name}/{file.filename}"
            await s3.add(file.file, s3_key)
        else:
            # ZIP upload
            zip_path = os.path.join(temp_dir, file.filename)
            with open(zip_path, "wb") as f:
                f.write(await file.read())

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(temp_dir)

            root_dir = find_index_root(temp_dir)
            # Upload ONLY that folder's contents
            for root, _, files in os.walk(root_dir):
                for filename in files:
                    local_path = os.path.join(root, filename)

                    relative_path = os.path.relpath(local_path, root_dir)
                    s3_key = f"projects/{name}/{relative_path.replace(os.sep, '/')}"

                    with open(local_path, "rb") as f:
                        await s3.add(f, s3_key)

    except HTTPException:
        await db.delete(new_project)
        await db.commit()
        raise

    except Exception as e:
        # Rollback DB if upload fails
        await db.delete(new_project)
        await db.commit()
        raise HTTPException(status_code=500, detail=f"S3 upload failed: {str(e)}")
    finally:
        shutil.rmtree(temp_dir)
    try:
        # Log the activity
        log = Activity(
            user_id=request.state.user_id,
            action="NEW PROJECT CREATED:" + name,
        )
        db.add(log)
        await db.commit()
    except:
        pass
    
    
    return {
        "message": "Project created and file uploaded successfully",
        "project_id": new_project.id,
    }

async def update_project_view(
    project_id: int,
    file: UploadFile,
    db: AsyncSession,
    request: Request
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if str(project.owner_id) != request.state.user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413, # Payload Too Large
            detail="File size exceeds the 20MB limit."
        )

    # Delete existing files
    await s3.delete_prefix(f"projects/{project.name}/")
        # Reuse upload logic
    await db.delete(project)
    try:
        # Log the activity
        log = Activity(
            user_id=request.state.user_id,
            action="PROJECT UPDATED: " + project.name,
        )
        db.add(log)
        await db.commit()
    except:
        pass
    await db.commit()
    await upload_project_view(
        name=project.name,
        file=file,
        db=db,
        request=request
    )


    # project.updated_at = datetime.utcnow()
    # await db.commit()

    return {"message": "Project updated successfully"}



async def get_all_project_view(db: AsyncSession, request: Request):
    result = await db.execute(
        select(Project).where(Project.owner_id == request.state.user_id).order_by(Project.id.desc())
    )
    all_projects = result.scalars().all()
    if not all_projects:
        raise HTTPException(status_code=200, detail="No projects exist for you")

    return {"projects": [{"id": p.id, "name": p.name, "created_at": p.created_at} for p in all_projects]}


async def get_user_project_view(db: AsyncSession, request: Request, user_email: str):
    user = await db.scalar(select(Users).where(Users.email == user_email))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(select(Project).where(Project.owner_id == user.id).order_by(Project.id.desc()))
    projects = result.scalars().all()

    return {
        "user_email": user_email,
        "projects": [{"id": p.id, "name": p.name, "created_at": p.created_at} for p in projects]
    }


async def delete_project_view(project_id: int, db: AsyncSession, request: Request):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if str(project.owner_id) != request.state.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this project")

    try:
        await s3.delete_prefix(f"projects/{project.name}/")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete project files from S3: {str(e)}")

    try:
        await db.delete(project)

        # Log the activity
        log = Activity(
            user_id=request.state.user_id,
            action="PROJECT DELETED: " + project.name,
        )
        db.add(log)
        await db.commit()

        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete project from database: {str(e)}")

    return {"message": f"Project '{project.name}' deleted successfully"}
