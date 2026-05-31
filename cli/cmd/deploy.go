package cmd

import (
	"bufio"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"strconv"
	"strings"

	"github.com/yukihito-jokyu/context/cli/internal/errs"
	"github.com/yukihito-jokyu/context/cli/internal/filesystem"
	"github.com/yukihito-jokyu/context/cli/internal/project"
	"github.com/yukihito-jokyu/context/cli/internal/prompt"
	"github.com/yukihito-jokyu/context/cli/internal/session"
)

type deployCommand struct {
	in              io.Reader
	out             io.Writer
	errOut          io.Writer
	getwd           func() (string, error)
	interactive     func() bool
	locator         filesystem.ContextLocator
	inspector       gitInspector
	listProjects    func(string) ([]project.Project, error)
	resolveProject  func(string, string) (project.Project, error)
	suggestProjects func([]project.Project, string, int) []string
}

type gitInspector func(string) (bool, string, error)

type commandRunner func(name string, args ...string) *exec.Cmd

var (
	stdinStat                = func() (os.FileInfo, error) { return os.Stdin.Stat() }
	execRunner commandRunner = exec.Command
)

func newDeployCommand(in io.Reader, out, errOut io.Writer) *deployCommand {
	return &deployCommand{
		in:              in,
		out:             out,
		errOut:          errOut,
		getwd:           os.Getwd,
		interactive:     isInteractiveStdin,
		locator:         filesystem.NewContextLocator(),
		inspector:       inspectGitRepository,
		listProjects:    project.List,
		resolveProject:  project.Resolve,
		suggestProjects: project.Suggest,
	}
}

func (c *deployCommand) run(args []string) error {
	if len(args) > 1 {
		return usageError("deploy accepts at most one repo-name")
	}

	cwd, err := c.getwd()
	if err != nil {
		return fmt.Errorf("failed to determine current directory: %w", err)
	}

	root, err := c.locator.Resolve(filesystem.ResolveParams{
		ExplicitRoot: os.Getenv("CONTEXT_REPO"),
		StartDir:     cwd,
	})
	if err != nil {
		return err
	}

	listProjects := c.listProjects
	if listProjects == nil {
		listProjects = project.List
	}
	resolveProject := c.resolveProject
	if resolveProject == nil {
		resolveProject = project.Resolve
	}
	suggestProjects := c.suggestProjects
	if suggestProjects == nil {
		suggestProjects = project.Suggest
	}

	projects, err := listProjects(root.ProjectsDir())
	if err != nil {
		return fmt.Errorf("failed to list projects: %w", err)
	}

	var selected project.Project
	if len(args) == 0 {
		if !c.interactive() {
			return fmt.Errorf("%w\nUsage:\n  context deploy <repo-name>", errs.ErrRepoNameRequired)
		}
		selected, err = c.selectProject(projects)
		if err != nil {
			return err
		}
	} else {
		selected, err = resolveProject(root.ProjectsDir(), args[0])
		if err != nil {
			var notFound errs.ProjectNotFoundError
			if errors.As(err, &notFound) {
				suggestions := suggestProjects(projects, args[0], 3)
				return prompt.FormatProjectNotFound(args[0], suggestions)
			}
			return err
		}
	}

	gitOK, gitRoot, gitErr := c.inspector(cwd)
	if gitErr != nil {
		fmt.Fprintf(c.errOut, "warning: failed to inspect git repository: %s\n", gitErr)
	}
	if !gitOK {
		fmt.Fprintln(c.errOut, "warning: current directory is not a git repository")
	}

	deploySession := session.New(root, &selected, cwd, gitOK, gitRoot)
	return prompt.PrintSessionStarted(c.out, &deploySession)
}

func (c *deployCommand) selectProject(projects []project.Project) (project.Project, error) {
	if len(projects) == 0 {
		return project.Project{}, errs.ErrNoProjects
	}

	fmt.Fprintln(c.out, "Select project:")
	for i, p := range projects {
		fmt.Fprintf(c.out, "  %d. %s\n", i+1, p.Name)
	}
	fmt.Fprint(c.out, "> ")

	scanner := bufio.NewScanner(c.in)
	if !scanner.Scan() {
		if err := scanner.Err(); err != nil {
			return project.Project{}, fmt.Errorf("failed to read project selection: %w", err)
		}
		return project.Project{}, errs.ErrProjectSelectionMissing
	}

	input := strings.TrimSpace(scanner.Text())
	index, err := strconv.Atoi(input)
	if err != nil || index < 1 || index > len(projects) {
		return project.Project{}, fmt.Errorf("%w: %s", errs.ErrInvalidProjectSelection, input)
	}

	return projects[index-1], nil
}

func isInteractiveStdin() bool {
	info, err := stdinStat()
	if err != nil {
		return false
	}
	return info.Mode()&os.ModeCharDevice != 0
}

func inspectGitRepository(dir string) (gitOK bool, gitRoot string, err error) {
	cmd := execRunner("git", "rev-parse", "--show-toplevel")
	cmd.Dir = dir
	output, err := cmd.Output()
	if err != nil {
		var exitErr *exec.ExitError
		if errors.As(err, &exitErr) {
			return false, "", nil
		}
		return false, "", err
	}

	return true, strings.TrimSpace(string(output)), nil
}
