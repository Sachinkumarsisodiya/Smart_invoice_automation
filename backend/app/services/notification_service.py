import uuid
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc

from app.models.notification import Notification, NotificationType
from app.models.user import User
from app.core.logging import logger


class NotificationService:
    @staticmethod
    def create_notification(
        db: Session,
        user_id: uuid.UUID,
        title: str,
        message: str,
        type: str = NotificationType.INFO,
        link: Optional[str] = None
    ) -> Notification:
        """Create an in-app notification for a specific user."""
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=type,
            link=link,
            is_read=False
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        logger.info(f"Notification created for user {user_id}: [{type}] {title}")
        return notification

    @staticmethod
    def create_role_notification(
        db: Session,
        roles: List[str],
        title: str,
        message: str,
        type: str = NotificationType.INFO,
        link: Optional[str] = None
    ) -> List[Notification]:
        """Broadcasts an in-app notification to all active users with specified roles."""
        users = db.scalars(
            select(User).where(User.role.in_(roles), User.is_active == True)
        ).all()

        notifications = []
        for u in users:
            n = Notification(
                user_id=u.id,
                title=title,
                message=message,
                type=type,
                link=link,
                is_read=False
            )
            db.add(n)
            notifications.append(n)

        if notifications:
            db.commit()
            for n in notifications:
                db.refresh(n)
            logger.info(f"Broadcasted notification '{title}' to {len(notifications)} users with roles {roles}")
        return notifications

    @staticmethod
    def get_user_notifications(
        db: Session,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
        unread_only: bool = False
    ) -> Tuple[List[Notification], int, int]:
        """Retrieve paginated notifications and counts for the authenticated user."""
        query = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            query = query.where(Notification.is_read == False)

        total = db.scalar(
            select(func.count(Notification.id)).where(Notification.user_id == user_id)
        ) or 0

        unread_count = db.scalar(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.is_read == False
            )
        ) or 0

        items = db.scalars(
            query.order_by(desc(Notification.created_at)).offset(skip).limit(limit)
        ).all()

        return items, total, unread_count

    @staticmethod
    def get_unread_count(db: Session, user_id: uuid.UUID) -> int:
        """Get the total unread notifications count for a user."""
        return db.scalar(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.is_read == False
            )
        ) or 0

    @staticmethod
    def mark_as_read(
        db: Session,
        notification_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[Notification]:
        """Marks a specific notification as read, ensuring ownership."""
        notification = db.scalar(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id
            )
        )
        if not notification:
            return None

        notification.is_read = True
        db.commit()
        db.refresh(notification)
        return notification

    @staticmethod
    def mark_all_read(db: Session, user_id: uuid.UUID) -> int:
        """Marks all unread notifications for a user as read."""
        unread_items = db.scalars(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.is_read == False
            )
        ).all()

        for item in unread_items:
            item.is_read = True

        db.commit()
        return len(unread_items)

    @staticmethod
    def delete_notification(
        db: Session,
        notification_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        """Dismisses/deletes a notification belonging to the user."""
        notification = db.scalar(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id
            )
        )
        if not notification:
            return False

        db.delete(notification)
        db.commit()
        return True
