package session

import (
	"github.com/yukihito-jokyu/context/cli/internal/filesystem"
	"github.com/yukihito-jokyu/context/cli/internal/project"
)

type DeploySession struct {
	ContextRoot           string
	ContextRootResolvedBy string
	Project               project.Project
	TargetDir             string
	TargetIsGitRepository bool
	TargetGitRoot         string
	SharedSkillsAvailable bool
	CompleteContextRoot   bool
	CanSelectSharedSkills bool
}

func New(root filesystem.ContextRoot, proj *project.Project, targetDir string, gitOK bool, gitRoot string) DeploySession {
	return DeploySession{
		ContextRoot:           root.Path,
		ContextRootResolvedBy: root.ResolvedBy,
		Project:               *proj,
		TargetDir:             targetDir,
		TargetIsGitRepository: gitOK,
		TargetGitRoot:         gitRoot,
		SharedSkillsAvailable: root.SharedSkillsExists,
		CompleteContextRoot:   root.Complete,
		CanSelectSharedSkills: root.SharedSkillsExists,
	}
}
