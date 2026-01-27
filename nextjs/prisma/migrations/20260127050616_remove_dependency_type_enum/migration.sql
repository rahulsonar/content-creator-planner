/*
  Warnings:

  - You are about to drop the column `dependencyType` on the `TaskDependency` table. All the data in the column will be lost.

*/
-- AlterTable
ALTER TABLE "TaskDependency" DROP COLUMN "dependencyType";

-- DropEnum
DROP TYPE "DependencyType";
