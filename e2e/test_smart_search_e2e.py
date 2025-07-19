#!/usr/bin/env python3

"""Tests for the Smart Search tools (find_definition, find_usages, find_imports)."""

import os
import unittest

from codemcp.testing import MCPEndToEndTestCase


class SmartSearchTest(MCPEndToEndTestCase):
    """Test the Smart Search tools for JavaScript/TypeScript code navigation."""

    async def asyncSetUp(self):
        """Set up the test environment with a git repository."""
        await super().asyncSetUp()

        # Create test files with various JavaScript/TypeScript patterns
        self.create_test_files()

        # Add our test files to git
        await self.git_run(["add", "."])
        await self.git_run(["commit", "-m", "Add test files for smart search"])

    def create_test_files(self):
        """Create test files with various JS/TS patterns for testing."""

        # Create a JavaScript file with classes and functions
        with open(os.path.join(self.temp_dir.name, "user-manager.js"), "w") as f:
            f.write("""// User management module
import { Database } from './database';
import { validateEmail, validatePhone } from './validators';

export class UserManager {
  constructor(database) {
    this.db = database;
  }

  async createUser(userData) {
    // Validate user data
    if (!validateEmail(userData.email)) {
      throw new Error('Invalid email');
    }

    const newUser = await this.db.users.create(userData);
    return newUser;
  }

  updateUser(id, updates) {
    // Update user in database
    return this.db.users.update(id, updates);
  }

  deleteUser(id) {
    return this.db.users.delete(id);
  }
}

export const getUserById = async (id) => {
  const manager = new UserManager(db);
  return await manager.getUser(id);
};

export default UserManager;
""")

        # Create a TypeScript file with interfaces and types
        with open(os.path.join(self.temp_dir.name, "types.ts"), "w") as f:
            f.write("""// Type definitions
export interface User {
  id: string;
  name: string;
  email: string;
  createdAt: Date;
}

export type UserRole = 'admin' | 'user' | 'guest';

export interface UserData extends User {
  role: UserRole;
  permissions: string[];
}

export enum UserStatus {
  Active = 'active',
  Inactive = 'inactive',
  Suspended = 'suspended'
}

type UpdateUserInput = Partial<User>;

const defaultUser: User = {
  id: '0',
  name: 'Guest',
  email: 'guest@example.com',
  createdAt: new Date()
};
""")

        # Create a React component file
        with open(os.path.join(self.temp_dir.name, "UserProfile.jsx"), "w") as f:
            f.write("""import React, { useState, useEffect } from 'react';
import { UserManager } from './user-manager';
import { User } from './types';

export const UserProfile = ({ userId }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const manager = new UserManager();
    manager.getUser(userId).then(userData => {
      setUser(userData);
      setLoading(false);
    });
  }, [userId]);

  if (loading) return <div>Loading...</div>;

  return (
    <div className="user-profile">
      <h1>{user.name}</h1>
      <p>{user.email}</p>
    </div>
  );
};

const ProfileCard = ({ user }) => {
  return <div>{user.name}</div>;
};

export default UserProfile;
""")

        # Create a file that uses the classes/functions
        with open(os.path.join(self.temp_dir.name, "app.js"), "w") as f:
            f.write("""import { UserManager } from './user-manager';
import UserProfile, { ProfileCard } from './UserProfile';
import { User, UserRole } from './types';

const manager = new UserManager(database);

async function main() {
  // Create a new user
  const newUser = await manager.createUser({
    name: 'John Doe',
    email: 'john@example.com'
  });

  // Update the user
  await manager.updateUser(newUser.id, { name: 'John Smith' });

  // Using the getUserById function
  const user = await getUserById('123');
  console.log(user);
}

// Test the validators
const isValid = validateEmail('test@example.com');

main().catch(console.error);
""")

        # Create a CommonJS file
        with open(os.path.join(self.temp_dir.name, "utils.cjs"), "w") as f:
            f.write("""const { UserManager } = require('./user-manager');
const validator = require('./validators');

function processUser(userData) {
  const manager = new UserManager();
  return manager.createUser(userData);
}

module.exports = {
  processUser,
  UserManager
};
""")

    async def test_find_definition_class(self):
        """Test finding class definitions."""
        async with self.create_client_session() as session:
            chat_id = await self.get_chat_id(session)

            # Find UserManager class definition
            result_text = await self.call_tool_assert_success(
                session,
                "codemcp",
                {
                    "subtool": "find_definition",
                    "symbol": "UserManager",
                    "path": self.temp_dir.name,
                    "chat_id": chat_id,
                },
            )

            # Verify results
            self.assertIn("user-manager.js", result_text)
            self.assertIn("export class UserManager", result_text)
            self.assertIn("class", result_text)  # Should identify it as a class

    async def test_find_definition_function(self):
        """Test finding function definitions."""
        async with self.create_client_session() as session:
            chat_id = await self.get_chat_id(session)

            # Find getUserById arrow function
            result_text = await self.call_tool_assert_success(
                session,
                "codemcp",
                {
                    "subtool": "find_definition",
                    "symbol": "getUserById",
                    "path": self.temp_dir.name,
                    "chat_id": chat_id,
                },
            )

            # Verify results
            self.assertIn("user-manager.js", result_text)
            self.assertIn("export const getUserById", result_text)
            self.assertIn("arrow_function", result_text)

    async def test_find_definition_interface(self):
        """Test finding TypeScript interface definitions."""
        async with self.create_client_session() as session:
            chat_id = await self.get_chat_id(session)

            # Find User interface
            result_text = await self.call_tool_assert_success(
                session,
                "codemcp",
                {
                    "subtool": "find_definition",
                    "symbol": "User",
                    "path": self.temp_dir.name,
                    "chat_id": chat_id,
                },
            )

            # Verify results
            self.assertIn("types.ts", result_text)
            self.assertIn("export interface User", result_text)
            self.assertIn("interface", result_text)

    async def test_find_definition_type_alias(self):
        """Test finding TypeScript type alias definitions."""
        async with self.create_client_session() as session:
            chat_id = await self.get_chat_id(session)

            # Find UserRole type
            result_text = await self.call_tool_assert_success(
                session,
                "codemcp",
                {
                    "subtool": "find_definition",
                    "symbol": "UserRole",
                    "path": self.temp_dir.name,
                    "chat_id": chat_id,
                },
            )

            # Verify results
            self.assertIn("types.ts", result_text)
            self.assertIn("export type UserRole", result_text)
            self.assertIn("type", result_text)

    async def test_find_definition_react_component(self):
        """Test finding React component definitions."""
        async with self.create_client_session() as session:
            chat_id = await self.get_chat_id(session)

            # Find UserProfile component
            result_text = await self.call_tool_assert_success(
                session,
                "codemcp",
                {
                    "subtool": "find_definition",
                    "symbol": "UserProfile",
                    "path": self.temp_dir.name,
                    "chat_id": chat_id,
                },
            )

            # Verify results
            self.assertIn("UserProfile.jsx", result_text)
            self.assertIn("export const UserProfile", result_text)

    async def test_find_usages_class(self):
        """Test finding class usages (instantiations)."""
        async with self.create_client_session() as session:
            chat_id = await self.get_chat_id(session)

            # Find UserManager usages
            result_text = await self.call_tool_assert_success(
                session,
                "codemcp",
                {
                    "subtool": "find_usages",
                    "symbol": "UserManager",
                    "path": self.temp_dir.name,
                    "chat_id": chat_id,
                },
            )

            # Verify results
            self.assertIn("app.js", result_text)
            self.assertIn("new UserManager", result_text)
            self.assertIn("UserProfile.jsx", result_text)
            # Should not include the definition file by default
            self.assertNotIn("export class UserManager", result_text)

    async def test_find_usages_function(self):
        """Test finding function call usages."""
        async with self.create_client_session() as session:
            chat_id = await self.get_chat_id(session)

            # Find createUser method calls
            result_text = await self.call_tool_assert_success(
                session,
                "codemcp",
                {
                    "subtool": "find_usages",
                    "symbol": "createUser",
                    "path": self.temp_dir.name,
                    "chat_id": chat_id,
                },
            )

            # Verify results
            self.assertIn("app.js", result_text)
            self.assertIn("manager.createUser", result_text)

    async def test_find_imports_es6(self):
        """Test finding ES6 import statements."""
        async with self.create_client_session() as session:
            chat_id = await self.get_chat_id(session)

            # Find UserManager imports
            result_text = await self.call_tool_assert_success(
                session,
                "codemcp",
                {
                    "subtool": "find_imports",
                    "module_or_symbol": "UserManager",
                    "path": self.temp_dir.name,
                    "chat_id": chat_id,
                },
            )

            # Verify results
            self.assertIn("app.js", result_text)
            self.assertIn("import { UserManager }", result_text)
            self.assertIn("UserProfile.jsx", result_text)

    async def test_find_imports_commonjs(self):
        """Test finding CommonJS require statements."""
        async with self.create_client_session() as session:
            chat_id = await self.get_chat_id(session)

            # Find UserManager require
            result_text = await self.call_tool_assert_success(
                session,
                "codemcp",
                {
                    "subtool": "find_imports",
                    "module_or_symbol": "UserManager",
                    "path": self.temp_dir.name,
                    "chat_id": chat_id,
                },
            )

            # Verify results
            self.assertIn("utils.cjs", result_text)
            self.assertIn("require", result_text)

    async def test_find_definition_not_found(self):
        """Test when a symbol definition is not found."""
        async with self.create_client_session() as session:
            chat_id = await self.get_chat_id(session)

            # Try to find a non-existent symbol
            result_text = await self.call_tool_assert_success(
                session,
                "codemcp",
                {
                    "subtool": "find_definition",
                    "symbol": "NonExistentClass",
                    "path": self.temp_dir.name,
                    "chat_id": chat_id,
                },
            )

            # Verify results
            self.assertIn("No definition found", result_text)
            self.assertIn("NonExistentClass", result_text)

    async def test_find_usages_with_exclude_definitions(self):
        """Test finding usages while excluding definitions."""
        async with self.create_client_session() as session:
            chat_id = await self.get_chat_id(session)

            # Find UserManager usages excluding definitions
            result_text = await self.call_tool_assert_success(
                session,
                "codemcp",
                {
                    "subtool": "find_usages",
                    "symbol": "UserManager",
                    "path": self.temp_dir.name,
                    "exclude_definitions": True,
                    "chat_id": chat_id,
                },
            )

            # Should not include the class definition
            self.assertNotIn("export class UserManager {", result_text)
            # Should include usages
            self.assertIn("new UserManager", result_text)

    async def test_find_definition_enum(self):
        """Test finding enum definitions."""
        async with self.create_client_session() as session:
            chat_id = await self.get_chat_id(session)

            # Find UserStatus enum
            result_text = await self.call_tool_assert_success(
                session,
                "codemcp",
                {
                    "subtool": "find_definition",
                    "symbol": "UserStatus",
                    "path": self.temp_dir.name,
                    "chat_id": chat_id,
                },
            )

            # Verify results
            self.assertIn("types.ts", result_text)
            self.assertIn("export enum UserStatus", result_text)
            self.assertIn("enum", result_text)


if __name__ == "__main__":
    unittest.main()
