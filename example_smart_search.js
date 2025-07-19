// Example JavaScript file to test smart search

export class UserManager {
  constructor(database) {
    this.db = database;
  }

  async createUser(userData) {
    // Create a new user
    return await this.db.users.create(userData);
  }

  updateUser(id, updates) {
    return this.db.users.update(id, updates);
  }
}

export const getUserById = async (id) => {
  const manager = new UserManager(db);
  return await manager.getUser(id);
};

function validateEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

// Using the functions
const result = validateEmail('test@example.com');
const user = getUserById(123);
