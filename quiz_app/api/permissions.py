from rest_framework.permissions import BasePermission


class IsQuizOwner(BasePermission):
    """Allow access only to the user who owns the quiz."""

    def has_object_permission(self, request, view, obj):
        """Return True if the quiz belongs to the requesting user."""
        return obj.user_id == request.user.id
