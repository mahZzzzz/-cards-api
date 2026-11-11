
---
name: prd-breakdown
description: Convert product requirement documents into small, independently testable draft cards.
---

# PRD Breakdown Skill

## When to Use

Use this skill when a user provides a Product Requirements Document (PRD) and wants to turn it into actionable project cards.

## Instructions

1. Read the PRD and identify its main sections.
2. Extract functional requirements, constraints, and acceptance criteria.
3. Divide large requirements into small, independently testable tasks.
4. Create a draft card for each task.
5. Each draft card must contain:
   - Title: a short, descriptive task name.
   - Goal: what the task should achieve.
   - Acceptance criteria: specific, testable conditions.
   - Dependencies: other tasks that must be completed first.
   - PRD section: the section supporting the task.
6. Do not invent requirements not supported by the PRD.
7. If information is missing or ambiguous, flag it explicitly.
8. Identify potential duplicates of existing cards.
9. Return draft cards for user review. Do not create actual cards without confirmation.

## Example 1: User Authentication

PRD section: 2.1 - User Authentication

Requirement:
Users must be able to register with email and password,
log in securely, and receive an error message when
authentication fails.

Draft Card 1:
- Title: Implement user registration
- Goal: Allow new users to create accounts.
- Acceptance criteria:
  - Users can register with valid email and password.
  - Invalid email formats are rejected.
  - Duplicate email addresses are rejected.
- Dependencies: User account storage.
- PRD section: 2.1 - User Authentication

Draft Card 2:
- Title: Implement user login
- Goal: Authenticate registered users.
- Acceptance criteria:
  - Valid credentials allow login.
  - Invalid credentials are rejected.
  - Passwords are not exposed in API responses.
- Dependencies: User registration.
- PRD section: 2.1 - User Authentication

Draft Card 3:
- Title: Display authentication error messages
- Goal: Inform users when login fails.
- Acceptance criteria:
  - Failed login attempts display an error message.
  - Error messages do not expose sensitive information.
- Dependencies: User login.
- PRD section: 2.1 - User Authentication


## Example 2: Task Assignment

PRD section: 3.2 - Card Assignment

Requirement:
Users must be able to assign and remove a responsible person from a card.

Draft card:
- Title: Implement card assignment
- Goal: Allow users to manage card ownership.
- Acceptance criteria:
  - A card can be assigned to a user.
  - The assignee can be changed.
  - The assignee can be removed.
  - Invalid assignee values are rejected.
- Dependencies: Card CRUD API.
- PRD section: 3.2 - Card Assignment

## Output Rules

- Return structured draft cards.
- Keep acceptance criteria measurable.
- Preserve the source PRD section for each card.
- Flag missing details and suspected duplicates.
- Require explicit user confirmation before saving cards.
