from fastapi import Request, HTTPException, Depends
import jwt
from config import settings

async def get_current_user(request: Request):
    # 1. Extract Token from Cookies
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        # 2. Decode and Validate
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        # 3. Extract data (Ensure your JWT creation logic includes 'id' and 'sub')
        user_id = payload.get("id")
        user_email = payload.get("sub")

        if user_id is None or user_email is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        # 4. Return a simple dictionary or a User object
        # Returning a dictionary is faster; fetching the full User from DB is more robust.
        return {"id": user_id, "email": user_email}

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except (jwt.InvalidTokenError, jwt.PyJWTError):
        raise HTTPException(status_code=401, detail="Invalid token")
