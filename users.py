# controller/routes/users.py
"""
User management routes for the Orchestration System.
Provides endpoints to list users and approvers.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
import logging
import os

from controller.db.db import get_db
from controller.deps import verify_token, require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


# =============================================================================
# Request/Response Models
# =============================================================================

class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., max_length=200)
    full_name: Optional[str] = Field(None, max_length=200)
    role: str = Field("user", pattern="^(user|approver|admin)$")


class UserUpdate(BaseModel):
    email: Optional[str] = Field(None, max_length=200)
    full_name: Optional[str] = Field(None, max_length=200)
    role: Optional[str] = Field(None, pattern="^(user|approver|admin)$")


class UserResponse(BaseModel):
    user_id: Optional[int] = None
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None


# =============================================================================
# Routes
# =============================================================================

@router.get("")
@router.get("/")
async def list_users(
    role: Optional[str] = Query(None, description="Filter by role (user, approver, admin)"),
    token: dict = Depends(verify_token)
):
    """List all users, optionally filtered by role"""
    db = get_db()
    
    try:
        users = db.list_users(role=role) if hasattr(db, 'list_users') else []
        return {
            "users": users,
            "count": len(users)
        }
    except Exception as e:
        logger.error(f"Error listing users: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/approvers")
async def list_approvers(
    token: dict = Depends(verify_token)
):
    """List all users who can approve workflows (approvers and admins)"""
    db = get_db()
    
    try:
        # Try to get users with approver or admin role
        approvers = []
        
        if hasattr(db, 'list_approvers'):
            approvers = db.list_approvers()
        elif hasattr(db, 'list_users'):
            all_users = db.list_users()
            approvers = [u for u in all_users if u.get('role') in ('approver', 'admin')]
        else:
            # Fallback: try raw SQL query
            try:
                conn = db.get_connection() if hasattr(db, 'get_connection') else None
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT user_id, username, email, full_name, role 
                        FROM users 
                        WHERE role IN ('approver', 'admin')
                        ORDER BY full_name, username
                    """)
                    rows = cursor.fetchall()
                    approvers = [
                        {
                            "user_id": row[0],
                            "username": row[1],
                            "email": row[2],
                            "full_name": row[3],
                            "role": row[4]
                        }
                        for row in rows
                    ]
            except Exception as sql_err:
                logger.warning(f"Could not query approvers directly: {sql_err}")
        
        return {
            "approvers": approvers,
            "count": len(approvers)
        }
    except Exception as e:
        logger.error(f"Error listing approvers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
@router.post("/")
async def create_user(
    user: UserCreate,
    admin: dict = Depends(require_admin)
):
    """Create a new user (admin only)"""
    db = get_db()
    
    try:
        # Check if user exists
        if hasattr(db, 'get_user_by_username'):
            existing = db.get_user_by_username(user.username)
            if existing:
                raise HTTPException(status_code=409, detail=f"User '{user.username}' already exists")
        
        # Create user
        if hasattr(db, 'create_user'):
            new_user = db.create_user(
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                role=user.role
            )
        else:
            # Fallback: direct SQL insert
            conn = db.get_connection() if hasattr(db, 'get_connection') else None
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (username, email, full_name, role)
                    VALUES (?, ?, ?, ?)
                """, (user.username, user.email, user.full_name, user.role))
                conn.commit()
                new_user = {
                    "user_id": cursor.lastrowid,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role
                }
            else:
                raise HTTPException(status_code=501, detail="User creation not supported")
        
        logger.info(f"User created: {user.username} with role {user.role}")
        return {
            "message": "User created successfully",
            "user": new_user
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{username}")
async def update_user(
    username: str,
    updates: UserUpdate,
    admin: dict = Depends(require_admin)
):
    """Update a user (admin only)"""
    db = get_db()
    
    try:
        if hasattr(db, 'update_user'):
            updated = db.update_user(username, updates.dict(exclude_none=True))
        else:
            # Fallback: direct SQL update
            conn = db.get_connection() if hasattr(db, 'get_connection') else None
            if conn:
                update_fields = []
                params = []
                if updates.email is not None:
                    update_fields.append("email = ?")
                    params.append(updates.email)
                if updates.full_name is not None:
                    update_fields.append("full_name = ?")
                    params.append(updates.full_name)
                if updates.role is not None:
                    update_fields.append("role = ?")
                    params.append(updates.role)
                
                if update_fields:
                    params.append(username)
                    cursor = conn.cursor()
                    cursor.execute(f"""
                        UPDATE users SET {', '.join(update_fields)}
                        WHERE username = ?
                    """, params)
                    conn.commit()
                    
                    if cursor.rowcount == 0:
                        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
                    
                updated = {"username": username, **updates.dict(exclude_none=True)}
            else:
                raise HTTPException(status_code=501, detail="User update not supported")
        
        logger.info(f"User updated: {username}")
        return {
            "message": "User updated successfully",
            "user": updated
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{username}")
async def delete_user(
    username: str,
    admin: dict = Depends(require_admin)
):
    """Delete a user (admin only)"""
    db = get_db()
    
    try:
        if hasattr(db, 'delete_user'):
            db.delete_user(username)
        else:
            conn = db.get_connection() if hasattr(db, 'get_connection') else None
            if conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE username = ?", (username,))
                conn.commit()
                
                if cursor.rowcount == 0:
                    raise HTTPException(status_code=404, detail=f"User '{username}' not found")
            else:
                raise HTTPException(status_code=501, detail="User deletion not supported")
        
        logger.info(f"User deleted: {username}")
        return {"message": f"User '{username}' deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
