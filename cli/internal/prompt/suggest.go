package prompt

import (
	"fmt"
	"io"
	"strings"

	"github.com/yukihito-jokyu/context/cli/internal/errs"
	"github.com/yukihito-jokyu/context/cli/internal/session"
)

func FormatProjectNotFound(name string, suggestions []string) error {
	if len(suggestions) == 0 {
		return fmt.Errorf("%w: %s", errs.ErrProjectNotFound, name)
	}

	lines := []string{
		fmt.Sprintf("project not found: %s", name),
		"",
		"Did you mean?",
	}
	for _, suggestion := range suggestions {
		lines = append(lines, "  - "+suggestion)
	}

	return fmt.Errorf("%w:\n%s", errs.ErrProjectNotFound, strings.Join(lines, "\n"))
}

func PrintSessionStarted(out io.Writer, deploySession *session.DeploySession) error {
	_, err := fmt.Fprintf(
		out,
		"Deploy session started\ncontext root: %s\nresolved by: %s\nproject: %s\nproject path: %s\ntarget: %s\nshared skills available: %t\ncomplete context root: %t\ngit repository: %t\n",
		deploySession.ContextRoot,
		deploySession.ContextRootResolvedBy,
		deploySession.Project.Name,
		deploySession.Project.Path,
		deploySession.TargetDir,
		deploySession.SharedSkillsAvailable,
		deploySession.CompleteContextRoot,
		deploySession.TargetIsGitRepository,
	)
	return err
}
