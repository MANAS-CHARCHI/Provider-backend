import functools
from fastapi import HTTPException, Request
import jwt
from config import settings

def login_required(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract 'request' from the function arguments
        request: Request = kwargs.get("request")
        if not request:
            # Fallback if request is passed as a positional argument
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
        
        if not request:
            raise RuntimeError("Decorator 'login_required' requires a 'Request' argument in the function.")

        # Token Logic
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(status_code=401, detail="Authentication required")

        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            request.state.user_email = payload.get("sub")
            request.state.user_id = payload.get("id")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        # Execute the original function
        return await func(*args, **kwargs)
    return wrapper

def role_required(required_role: str):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract 'request' from the function arguments
            request: Request = kwargs.get("request")
            if not request:
                # Fallback if request is passed as a positional argument
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if not request:
                raise RuntimeError("Decorator 'role_required' requires a 'Request' argument in the function.")

            # Token Logic
            token = request.cookies.get("access_token")
            if not token:
                raise HTTPException(status_code=401, detail="Authentication required")

            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                user_role = payload.get("role")
                if user_role not in required_role:
                    print( "role by token is:", user_role, " required_role is:", required_role)
                    raise HTTPException(status_code=403, detail="Insufficient permissions")
                request.state.user_email = payload.get("sub")
            except jwt.ExpiredSignatureError:
                raise HTTPException(status_code=401, detail="Token expired")
            except jwt.InvalidTokenError:
                raise HTTPException(status_code=401, detail="Invalid token")
            except jwt.PyJWTError:
                raise HTTPException(status_code=401, detail="Invalid or expired token")

            # Execute the original function
            return await func(*args, **kwargs)
        return wrapper
    return decorator