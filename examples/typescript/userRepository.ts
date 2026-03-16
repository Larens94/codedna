/**
 * CRUD operations for User entity with TypeORM.
 *
 * Module (CodeDNA v0.5):
 *   file: userRepository.ts
 *   purpose: Data access layer for User entity — find, save operations
 *   deps: entities/User.ts (User), db.ts (AppDataSource)
 *   exports: findById(id) → Promise<User|null>, findByEmail(email) → Promise<User|null>, save(user) → Promise<User>
 *   rules:
 *     - All queries go through TypeORM repository — no raw SQL
 *     - findById and findByEmail return null if not found — callers MUST check
 *     - save() handles both insert and update (TypeORM upsert)
 */

import { AppDataSource } from './db';
// User entity with TypeORM decorators — see entities/User.ts
import { User } from './entities/User';

const repo = AppDataSource.getRepository(User);

/**
 * Find a user by primary key.
 *
 * @param id - User UUID
 * @returns User entity or null if not found
 *
 * Used by: authService.ts → session validation
 */
export async function findById(id: string): Promise<User | null> {
  return repo.findOneBy({ id });
}

/**
 * Find a user by email address.
 *
 * @param email - User email (unique)
 * @returns User entity or null if not found
 *
 * Used by: authService.ts → login flow
 */
export async function findByEmail(email: string): Promise<User | null> {
  return repo.findOneBy({ email });
}

/**
 * Persist a User entity (insert or update).
 *
 * @param user - Partial or full User entity
 * @returns Saved User with generated fields populated
 *
 * Used by: userController.ts → POST /users, PATCH /users/:id
 */
export async function save(user: Partial<User>): Promise<User> {
  return repo.save(user);
}
