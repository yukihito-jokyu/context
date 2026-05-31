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

	"github.com/yukihito-jokyu/context/cli/internal/agents"
	"github.com/yukihito-jokyu/context/cli/internal/errs"
	"github.com/yukihito-jokyu/context/cli/internal/filesystem"
	"github.com/yukihito-jokyu/context/cli/internal/project"
	"github.com/yukihito-jokyu/context/cli/internal/prompt"
	"github.com/yukihito-jokyu/context/cli/internal/session"
	"github.com/yukihito-jokyu/context/cli/internal/skill"
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
	lineScanner     *bufio.Scanner
}

type gitInspector func(string) (bool, string, error)

type agentsPromptState struct {
	available bool
}

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
	c.lineScanner = nil

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
	if err := prompt.PrintSessionStarted(c.out, &deploySession); err != nil {
		return err
	}

	candidates, err := skill.Collect(root.UtilsSkillsDir(), selected.SkillsDir)
	if err != nil {
		return err
	}

	chosen := candidates
	if c.interactive() {
		if len(candidates) > 0 {
			chosen, err = c.selectSkills(candidates)
			if err != nil {
				return err
			}
		} else {
			fmt.Fprintf(c.out, "No skills found for project: %s\n", selected.Name)
		}
	} else if len(candidates) == 0 {
		fmt.Fprintf(c.out, "No skills found for project: %s\n", selected.Name)
	}

	deployAgents := false
	generateClaude := false
	if c.interactive() {
		agentsState, err := c.inspectAgentsPath(&selected)
		if err != nil {
			return err
		}
		deployAgents, err = c.selectAgents(agentsState)
		if err != nil {
			return err
		}
		generateClaude, err = c.selectClaude(agentsState)
		if err != nil {
			return err
		}
	}

	if len(chosen) > 0 {
		if err := skill.DeployToAgents(cwd, chosen); err != nil {
			return err
		}
	}
	if deployAgents {
		if err := agents.Deploy(cwd, selected.AgentsPath); err != nil {
			return err
		}
	}
	if generateClaude {
		if err := agents.GenerateClaude(cwd, selected.AgentsPath); err != nil {
			return err
		}
	}
	return nil
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

	input, err := c.readLine()
	if err != nil {
		if !errors.Is(err, io.EOF) {
			return project.Project{}, fmt.Errorf("failed to read project selection: %w", err)
		}
		return project.Project{}, errs.ErrProjectSelectionMissing
	}

	index, err := strconv.Atoi(strings.TrimSpace(input))
	if err != nil || index < 1 || index > len(projects) {
		return project.Project{}, fmt.Errorf("%w: %s", errs.ErrInvalidProjectSelection, input)
	}

	return projects[index-1], nil
}

func (c *deployCommand) selectSkills(candidates []skill.Candidate) ([]skill.Candidate, error) {
	if len(candidates) == 0 {
		return nil, errs.ErrNoSkillsFound
	}

	fmt.Fprintln(c.out, "Select skills to deploy:")
	for i, candidate := range candidates {
		fmt.Fprintf(c.out, "  %d. %s (%s)\n", i+1, candidate.Name, candidate.Source)
	}
	fmt.Fprint(c.out, "> ")

	input, err := c.readLine()
	if err != nil {
		if !errors.Is(err, io.EOF) {
			return nil, fmt.Errorf("failed to read skill selection: %w", err)
		}
		return nil, errs.ErrSkillSelectionMissing
	}

	input = strings.TrimSpace(input)
	if input == "" {
		return nil, errs.ErrSkillSelectionMissing
	}

	indexes := strings.Split(input, ",")
	selected := make([]skill.Candidate, 0, len(indexes))
	seen := make(map[int]struct{}, len(indexes))
	for _, raw := range indexes {
		index, err := strconv.Atoi(strings.TrimSpace(raw))
		if err != nil || index < 1 || index > len(candidates) {
			return nil, fmt.Errorf("%w: %s", errs.ErrInvalidSkillSelection, raw)
		}
		if _, ok := seen[index]; ok {
			continue
		}
		seen[index] = struct{}{}
		selected = append(selected, candidates[index-1])
	}

	return selected, nil
}

func (c *deployCommand) inspectAgentsPath(selected *project.Project) (agentsPromptState, error) {
	info, err := os.Stat(selected.AgentsPath)
	if err != nil {
		if os.IsNotExist(err) {
			fmt.Fprintf(c.out, "AGENTS.md not found for project %s. Skipping AGENTS.md deploy and CLAUDE.md generation.\n", selected.Name)
			return agentsPromptState{}, nil
		}
		return agentsPromptState{}, fmt.Errorf("failed to stat AGENTS.md: %w", err)
	}
	if info.IsDir() {
		return agentsPromptState{}, fmt.Errorf("%w: %s", errs.ErrInvalidAgentsPath, selected.AgentsPath)
	}

	return agentsPromptState{available: true}, nil
}

func (c *deployCommand) selectAgents(state agentsPromptState) (bool, error) {
	if !state.available {
		return false, nil
	}

	fmt.Fprint(c.out, "Deploy AGENTS.md from project? [y/N]: ")

	input, err := c.readLine()
	if err != nil {
		if !errors.Is(err, io.EOF) {
			return false, fmt.Errorf("failed to read AGENTS.md selection: %w", err)
		}
		return false, nil
	}

	input = strings.ToLower(strings.TrimSpace(input))
	switch input {
	case "", "n", "no":
		return false, nil
	case "y", "yes":
		return true, nil
	default:
		return false, fmt.Errorf("%w: %s", errs.ErrInvalidAgentsSelection, input)
	}
}

func (c *deployCommand) selectClaude(state agentsPromptState) (bool, error) {
	if !state.available {
		return false, nil
	}

	fmt.Fprint(c.out, "Generate CLAUDE.md from project AGENTS.md? [y/N]: ")

	input, err := c.readLine()
	if err != nil {
		if !errors.Is(err, io.EOF) {
			return false, fmt.Errorf("failed to read CLAUDE.md selection: %w", err)
		}
		return false, nil
	}

	input = strings.ToLower(strings.TrimSpace(input))
	switch input {
	case "", "n", "no":
		return false, nil
	case "y", "yes":
		return true, nil
	default:
		return false, fmt.Errorf("%w: %s", errs.ErrInvalidClaudeSelection, input)
	}
}

func (c *deployCommand) readLine() (string, error) {
	if c.lineScanner == nil {
		c.lineScanner = bufio.NewScanner(c.in)
	}
	if !c.lineScanner.Scan() {
		if err := c.lineScanner.Err(); err != nil {
			return "", err
		}
		return "", io.EOF
	}
	return c.lineScanner.Text(), nil
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
