/*
  Warnings:

  - The values [FINISH_TO_START,START_TO_START,FINISH_TO_FINISH,START_TO_FINISH] on the enum `DependencyType` will be removed. If these variants are still used in the database, this will fail.

*/
-- AlterEnum
BEGIN;
CREATE TYPE "DependencyType_new" AS ENUM ('DEPENDS_ON', 'BLOCKED_BY');
ALTER TABLE "public"."TaskDependency" ALTER COLUMN "dependencyType" DROP DEFAULT;
ALTER TABLE "TaskDependency" ALTER COLUMN "dependencyType" TYPE "DependencyType_new" USING ("dependencyType"::text::"DependencyType_new");
ALTER TYPE "DependencyType" RENAME TO "DependencyType_old";
ALTER TYPE "DependencyType_new" RENAME TO "DependencyType";
DROP TYPE "public"."DependencyType_old";
ALTER TABLE "TaskDependency" ALTER COLUMN "dependencyType" SET DEFAULT 'DEPENDS_ON';
COMMIT;

-- AlterTable
ALTER TABLE "TaskDependency" ALTER COLUMN "dependencyType" SET DEFAULT 'DEPENDS_ON';
