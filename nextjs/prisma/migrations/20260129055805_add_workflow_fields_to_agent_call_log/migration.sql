-- AlterTable
ALTER TABLE "AgentCallLog" ADD COLUMN     "completionScore" DOUBLE PRECISION,
ADD COLUMN     "gapsIdentified" INTEGER,
ADD COLUMN     "iterationNumber" INTEGER,
ADD COLUMN     "parentCallId" TEXT,
ADD COLUMN     "synthesisAction" TEXT,
ADD COLUMN     "taskId" TEXT,
ADD COLUMN     "taskType" TEXT,
ADD COLUMN     "workflowPhase" TEXT;

-- CreateIndex
CREATE INDEX "AgentCallLog_iterationNumber_idx" ON "AgentCallLog"("iterationNumber");

-- CreateIndex
CREATE INDEX "AgentCallLog_workflowPhase_idx" ON "AgentCallLog"("workflowPhase");

-- CreateIndex
CREATE INDEX "AgentCallLog_parentCallId_idx" ON "AgentCallLog"("parentCallId");
