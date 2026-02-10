/*
  Warnings:

  - You are about to drop the `UserContext` table. If the table is not empty, all the data it contains will be lost.

*/
-- DropForeignKey
ALTER TABLE "UserContext" DROP CONSTRAINT "UserContext_userId_fkey";

-- DropTable
DROP TABLE "UserContext";
