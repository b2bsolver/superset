# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
"""
ENIM OAuth Security Manager for Superset.

This module provides a custom security manager that extends SupersetSecurityManager
to handle OAuth authentication from ENIM Core using Laravel Passport.
"""
import logging
import os
from typing import Any

from flask import session

from superset.security.manager import SupersetSecurityManager

logger = logging.getLogger(__name__)


class EnimOAuthSecurityManager(SupersetSecurityManager):
    """
    Custom security manager for ENIM OAuth authentication.

    This extends SupersetSecurityManager to handle OAuth user info
    from ENIM Core and store INF IDs for row-level security.
    """

    def oauth_user_info(self, provider: str, response: Any = None) -> dict[str, Any]:
        """
        Extract user information from OAuth provider response.

        Args:
            provider: OAuth provider name (e.g., "enim")
            response: OAuth response object

        Returns:
            Dictionary with user information
        """
        if provider == "enim":
            try:
                # Get user info from ENIM Core
                me = self.appbuilder.sm.oauth_remotes[provider].get("api/oauth/userinfo")
                data = me.json()

                # Store INF IDs in session for row-level security
                inf_ids = data.get("inf_ids", [])
                session["enim_inf_ids"] = inf_ids

                # Extract name parts
                name = data.get("name", "")
                name_parts = name.split() if name else [""]
                first_name = name_parts[0] if name_parts else ""
                last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

                # Generate username from email
                email = data.get("email", "")
                username = data.get("username", email.split("@")[0] if email else "")

                # Get user role from ENIM Core and map to Superset roles
                enim_role = data.get("role", "").lower()
                if enim_role == "admin":
                    role_keys = ["Admin"]
                else:
                    default_role = os.getenv("DEFAULT_ROLE_FOR_ENIM_USERS", "Gamma")
                    role_keys = [default_role]

                logger.info("OAuth user info retrieved for: %s with role: %s", email, enim_role)

                return {
                    "username": username,
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "role_keys": role_keys,
                }
            except Exception as e:
                logger.exception("Error getting OAuth user info: %s", str(e))
                return {}

        return super().oauth_user_info(provider, response)

    def auth_user_oauth(self, userinfo: dict[str, Any]) -> Any:
        """
        Authenticate and create/update OAuth user with role assignment.

        This overrides the parent method to properly assign roles based on
        the role_keys returned from oauth_user_info.

        Args:
            userinfo: User information from oauth_user_info

        Returns:
            User object or None
        """
        # Call parent method to create/update user
        user = super().auth_user_oauth(userinfo)

        if user and "role_keys" in userinfo:
            # Get roles from role_keys
            role_names = userinfo.get("role_keys", [])
            roles = []
            for role_name in role_names:
                role = self.find_role(role_name)
                if role:
                    roles.append(role)
                else:
                    logger.warning("Role '%s' not found in Superset", role_name)

            if roles:
                user.roles = roles
                self.update_user(user)
                logger.info("Updated user %s with roles: %s", user.username, role_names)

        return user

    def get_user_inf_ids(self) -> list[int]:
        """
        Get the current user's INF IDs from session.

        This can be used for row-level security filtering.

        Returns:
            List of INF IDs for the current user
        """
        return session.get("enim_inf_ids", [])
