/*
  Warnings:

  - The primary key for the `Task` table will be changed. If it partially fails, the table could be left without primary key constraint.
  - The `id` column on the `Task` table would be dropped and recreated. This will lead to data loss if there is data in the column.
  - The `parentId` column on the `Task` table would be dropped and recreated. This will lead to data loss if there is data in the column.
  - A unique constraint covering the columns `[taskKey]` on the table `Task` will be added. If there are existing duplicate values, this will fail.
  - Changed the type of `dependentId` on the `TaskDependency` table. No cast exists, the column would be dropped and recreated, which cannot be done if there is data, since the column is required.
  - Changed the type of `blockingId` on the `TaskDependency` table. No cast exists, the column would be dropped and recreated, which cannot be done if there is data, since the column is required.
  - Changed the type of `taskId` on the `TaskNote` table. No cast exists, the column would be dropped and recreated, which cannot be done if there is data, since the column is required.

*/
-- DropForeignKey
ALTER TABLE "Task" DROP CONSTRAINT "Task_parentId_fkey";

-- DropForeignKey
ALTER TABLE "TaskDependency" DROP CONSTRAINT "TaskDependency_blockingId_fkey";

-- DropForeignKey
ALTER TABLE "TaskDependency" DROP CONSTRAINT "TaskDependency_dependentId_fkey";

-- DropForeignKey
ALTER TABLE "TaskNote" DROP CONSTRAINT "TaskNote_taskId_fkey";

-- AlterTable
ALTER TABLE "Task" DROP CONSTRAINT "Task_pkey",
ADD COLUMN     "taskKey" TEXT,
DROP COLUMN "id",
ADD COLUMN     "id" SERIAL NOT NULL,
DROP COLUMN "parentId",
ADD COLUMN     "parentId" INTEGER,
ADD CONSTRAINT "Task_pkey" PRIMARY KEY ("id");

-- AlterTable
ALTER TABLE "TaskDependency" DROP COLUMN "dependentId",
ADD COLUMN     "dependentId" INTEGER NOT NULL,
DROP COLUMN "blockingId",
ADD COLUMN     "blockingId" INTEGER NOT NULL;

-- AlterTable
ALTER TABLE "TaskNote" DROP COLUMN "taskId",
ADD COLUMN     "taskId" INTEGER NOT NULL;

-- CreateIndex
CREATE UNIQUE INDEX "Task_taskKey_key" ON "Task"("taskKey");

-- CreateIndex
CREATE INDEX "Task_parentId_idx" ON "Task"("parentId");

-- CreateIndex
CREATE INDEX "TaskDependency_dependentId_idx" ON "TaskDependency"("dependentId");

-- CreateIndex
CREATE INDEX "TaskDependency_blockingId_idx" ON "TaskDependency"("blockingId");

-- CreateIndex
CREATE UNIQUE INDEX "TaskDependency_dependentId_blockingId_key" ON "TaskDependency"("dependentId", "blockingId");

-- CreateIndex
CREATE INDEX "TaskNote_taskId_idx" ON "TaskNote"("taskId");

-- AddForeignKey
ALTER TABLE "Task" ADD CONSTRAINT "Task_parentId_fkey" FOREIGN KEY ("parentId") REFERENCES "Task"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "TaskNote" ADD CONSTRAINT "TaskNote_taskId_fkey" FOREIGN KEY ("taskId") REFERENCES "Task"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "TaskDependency" ADD CONSTRAINT "TaskDependency_dependentId_fkey" FOREIGN KEY ("dependentId") REFERENCES "Task"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "TaskDependency" ADD CONSTRAINT "TaskDependency_blockingId_fkey" FOREIGN KEY ("blockingId") REFERENCES "Task"("id") ON DELETE CASCADE ON UPDATE CASCADE;
