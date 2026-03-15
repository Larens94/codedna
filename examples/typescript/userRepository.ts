// ==============================================================
// FILE: userRepository.ts
// PURPOSE: CRUD operations for User entity with TypeORM
// DEPENDS_ON: entities/User.ts → User, db.ts → AppDataSource
// EXPORTS: findById(id) → Promise<User|null>, save(user) → Promise<User>
//          findByEmail(email) → Promise<User|null>
// STYLE: TypeORM, async/await, no raw SQL
// DB_TABLES: users (id, email, name, created_at, updated_at)
// LAST_MODIFIED: initial Beacon Framework example
// ==============================================================

import { AppDataSource } from './db';
// → from entities/User.ts: User entity with TypeORM decorators
import { User } from './entities/User';

const repo = AppDataSource.getRepository(User);

/**
 * Find a user by primary key.
 * ← used by: authService.ts → session validation
 *
 * @param id - User UUID
 * @returns User entity or null if not found
 */
export async function findById(id: string): Promise<User | null> {
  return repo.findOneBy({ id });
}

/**
 * Find a user by email address.
 * ← used by: authService.ts → login flow
 *
 * @param email - User email (unique)
 * @returns User entity or null if not found
 */
export async function findByEmail(email: string): Promise<User | null> {
  return repo.findOneBy({ email });
}

/**
 * Persist a User entity (insert or update).
 * ← used by: userController.ts → POST /users, PATCH /users/:id
 *
 * @param user - Partial or full User entity
 * @returns Saved User with generated fields populated
 */
export async function save(user: Partial<User>): Promise<User> {
  return repo.save(user);
}
