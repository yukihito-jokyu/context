package cmd

import (
	"bytes"
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/yukihito-jokyu/context/cli/internal/errs"
	"github.com/yukihito-jokyu/context/cli/internal/filesystem"
	"github.com/yukihito-jokyu/context/cli/internal/project"
	"github.com/yukihito-jokyu/context/cli/internal/skill"
)

func TestDeployRun(t *testing.T) {
	repoRoot := makeContextRepo(t, []string{"alpha", "beta", "spring-batch", "spring-boot-api"})

	tests := []struct {
		name            string
		args            []string
		input           string
		cwd             string
		getwdErr        error
		inspector       gitInspector
		listProjects    func(string) ([]project.Project, error)
		resolveProject  func(string, string) (project.Project, error)
		suggestProjects func([]project.Project, string, int) []string
		wantErrText     string
		wantOutText     string
		wantErrOut      string
		wantErrIs       error
	}{
		{
			name:        "runs deploy for named project",
			args:        []string{"alpha"},
			cwd:         filepath.Join(repoRoot, "cli"),
			inspector:   func(string) (bool, string, error) { return true, filepath.Join(repoRoot, "cli"), nil },
			wantOutText: "project: alpha",
		},
		{
			name:        "selects project interactively and prints git warning",
			input:       "2\n",
			cwd:         filepath.Join(repoRoot, "cli"),
			inspector:   func(string) (bool, string, error) { return false, "", errors.New("git unavailable") },
			wantOutText: "project: beta",
			wantErrOut:  "warning: failed to inspect git repository: git unavailable\nwarning: current directory is not a git repository\n",
		},
		{
			name:        "returns interactive selection error",
			input:       "0\n",
			cwd:         filepath.Join(repoRoot, "cli"),
			inspector:   func(string) (bool, string, error) { return true, filepath.Join(repoRoot, "cli"), nil },
			wantErrText: "invalid project selection",
		},
		{
			name:        "suggests similar projects when missing",
			args:        []string{"spring"},
			cwd:         filepath.Join(repoRoot, "cli"),
			inspector:   func(string) (bool, string, error) { return true, filepath.Join(repoRoot, "cli"), nil },
			wantErrText: "Did you mean?",
		},
		{
			name:        "rejects invalid project name",
			args:        []string{"../alpha"},
			cwd:         filepath.Join(repoRoot, "cli"),
			inspector:   func(string) (bool, string, error) { return true, filepath.Join(repoRoot, "cli"), nil },
			wantErrText: "invalid project name: ../alpha",
		},
		{
			name:        "rejects too many args",
			args:        []string{"alpha", "beta"},
			wantErrIs:   errs.ErrUsage,
			wantErrText: "deploy accepts at most one repo-name",
		},
		{
			name:        "returns current directory error",
			getwdErr:    errors.New("cwd failed"),
			wantErrText: "failed to determine current directory",
		},
		{
			name: "returns locator error",
			args: []string{"alpha"},
			cwd:  t.TempDir(),
			inspector: func(string) (bool, string, error) {
				return true, filepath.Join(repoRoot, "cli"), nil
			},
			wantErrText: "failed to locate context repository root",
		},
		{
			name: "returns list error",
			args: []string{"alpha"},
			cwd:  filepath.Join(repoRoot, "cli"),
			inspector: func(string) (bool, string, error) {
				return true, filepath.Join(repoRoot, "cli"), nil
			},
			listProjects: func(string) ([]project.Project, error) {
				return nil, errors.New("list failed")
			},
			wantErrText: "failed to list projects: list failed",
		},
		{
			name: "returns resolve error",
			args: []string{"alpha"},
			cwd:  filepath.Join(repoRoot, "cli"),
			inspector: func(string) (bool, string, error) {
				return true, filepath.Join(repoRoot, "cli"), nil
			},
			resolveProject: func(string, string) (project.Project, error) {
				return project.Project{}, errors.New("resolve failed")
			},
			wantErrText: "resolve failed",
		},
		{
			name:        "requires repo name in non interactive mode",
			cwd:         filepath.Join(repoRoot, "cli"),
			inspector:   func(string) (bool, string, error) { return true, filepath.Join(repoRoot, "cli"), nil },
			wantErrText: "repo-name is required in non-interactive mode",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if tt.name != "returns locator error" {
				t.Setenv("CONTEXT_REPO", repoRoot)
			}

			var stdout bytes.Buffer
			var stderr bytes.Buffer

			command := deployCommand{
				in:      strings.NewReader(tt.input),
				out:     &stdout,
				errOut:  &stderr,
				locator: filesystem.NewContextLocator(),
				getwd: func() (string, error) {
					if tt.getwdErr != nil {
						return "", tt.getwdErr
					}
					return tt.cwd, nil
				},
				interactive:     func() bool { return tt.input != "" || len(tt.args) > 0 },
				inspector:       tt.inspector,
				listProjects:    tt.listProjects,
				resolveProject:  tt.resolveProject,
				suggestProjects: tt.suggestProjects,
			}

			err := command.run(tt.args)
			if tt.wantErrIs != nil && !errors.Is(err, tt.wantErrIs) {
				t.Fatalf("expected error %v, got %v", tt.wantErrIs, err)
			}
			if tt.wantErrText == "" && err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if tt.wantErrText != "" {
				if err == nil || !strings.Contains(err.Error(), tt.wantErrText) {
					t.Fatalf("expected error containing %q, got %v", tt.wantErrText, err)
				}
			}
			if tt.wantOutText != "" && !strings.Contains(stdout.String(), tt.wantOutText) {
				t.Fatalf("expected stdout containing %q, got %q", tt.wantOutText, stdout.String())
			}
			if stderr.String() != tt.wantErrOut {
				t.Fatalf("expected stderr %q, got %q", tt.wantErrOut, stderr.String())
			}
		})
	}
}

func TestDeployRunDeploysSelectedSkills(t *testing.T) {
	repoRoot := makeContextRepo(t, []string{"alpha"})
	targetDir := t.TempDir()

	writeSkillFixture(t, filepath.Join(repoRoot, "utils", "skills"), "override", "shared override", true)
	writeSkillFixture(t, filepath.Join(repoRoot, "utils", "skills"), "shared-only", "shared only", true)
	writeSkillFixture(t, filepath.Join(repoRoot, "utils", "skills"), "ignored-no-skill", "", false)
	writeSkillFixture(t, filepath.Join(repoRoot, "projects", "alpha", "skills"), "override", "project override", true)

	t.Setenv("CONTEXT_REPO", repoRoot)

	var stdout bytes.Buffer
	var stderr bytes.Buffer

	command := deployCommand{
		in:          strings.NewReader("1\n"),
		out:         &stdout,
		errOut:      &stderr,
		locator:     filesystem.NewContextLocator(),
		getwd:       func() (string, error) { return targetDir, nil },
		interactive: func() bool { return true },
		inspector:   func(string) (bool, string, error) { return true, targetDir, nil },
	}

	if err := command.run([]string{"alpha"}); err != nil {
		t.Fatalf("run returned error: %v", err)
	}

	for _, agentDir := range []string{".claude/skills/override", ".codex/skills/override"} {
		skillPath := filepath.Join(targetDir, agentDir, "SKILL.md")
		content, err := os.ReadFile(skillPath)
		if err != nil {
			t.Fatalf("failed to read %s: %v", skillPath, err)
		}
		if string(content) != "project override" {
			t.Fatalf("expected project skill content in %s, got %q", skillPath, string(content))
		}

		readmePath := filepath.Join(targetDir, agentDir, "README.md")
		if _, err := os.Stat(readmePath); !errors.Is(err, os.ErrNotExist) {
			t.Fatalf("expected README to be excluded from %s, got err=%v", readmePath, err)
		}
	}

	if _, err := os.Stat(filepath.Join(targetDir, ".claude", "skills", "shared-only")); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("expected unselected skill to be absent, got err=%v", err)
	}
	if !strings.Contains(stdout.String(), "Select skills to deploy:") {
		t.Fatalf("expected skill selection prompt, got %q", stdout.String())
	}
	if stderr.Len() != 0 {
		t.Fatalf("expected empty stderr, got %q", stderr.String())
	}
}

func TestDeployRunDeploysAllSkillsInNonInteractiveMode(t *testing.T) {
	repoRoot := makeContextRepo(t, []string{"alpha"})
	targetDir := t.TempDir()

	writeSkillFixture(t, filepath.Join(repoRoot, "utils", "skills"), "shared-only", "shared only", true)
	writeSkillFixture(t, filepath.Join(repoRoot, "projects", "alpha", "skills"), "override", "project override", true)

	t.Setenv("CONTEXT_REPO", repoRoot)

	var stdout bytes.Buffer
	var stderr bytes.Buffer

	command := deployCommand{
		in:          strings.NewReader(""),
		out:         &stdout,
		errOut:      &stderr,
		locator:     filesystem.NewContextLocator(),
		getwd:       func() (string, error) { return targetDir, nil },
		interactive: func() bool { return false },
		inspector:   func(string) (bool, string, error) { return true, targetDir, nil },
	}

	if err := command.run([]string{"alpha"}); err != nil {
		t.Fatalf("run returned error: %v", err)
	}

	for path, want := range map[string]string{
		filepath.Join(targetDir, ".claude", "skills", "override", "SKILL.md"):    "project override",
		filepath.Join(targetDir, ".codex", "skills", "override", "SKILL.md"):     "project override",
		filepath.Join(targetDir, ".claude", "skills", "shared-only", "SKILL.md"): "shared only",
		filepath.Join(targetDir, ".codex", "skills", "shared-only", "SKILL.md"):  "shared only",
	} {
		content, err := os.ReadFile(path)
		if err != nil {
			t.Fatalf("failed to read %s: %v", path, err)
		}
		if string(content) != want {
			t.Fatalf("expected %q in %s, got %q", want, path, string(content))
		}
	}

	if strings.Contains(stdout.String(), "Select skills to deploy:") {
		t.Fatalf("did not expect skill selection prompt in non-interactive mode, got %q", stdout.String())
	}
	if stderr.Len() != 0 {
		t.Fatalf("expected empty stderr, got %q", stderr.String())
	}
}

func TestDeployRunDeploysProjectAgentsWhenSelected(t *testing.T) {
	repoRoot := makeContextRepo(t, []string{"alpha"})
	targetDir := t.TempDir()

	agentsPath := filepath.Join(repoRoot, "projects", "alpha", "AGENTS.md")
	if err := os.WriteFile(agentsPath, []byte("project agents"), 0o644); err != nil {
		t.Fatalf("failed to create AGENTS.md: %v", err)
	}

	t.Setenv("CONTEXT_REPO", repoRoot)

	var stdout bytes.Buffer
	var stderr bytes.Buffer

	command := deployCommand{
		in:          strings.NewReader("y\n"),
		out:         &stdout,
		errOut:      &stderr,
		locator:     filesystem.NewContextLocator(),
		getwd:       func() (string, error) { return targetDir, nil },
		interactive: func() bool { return true },
		inspector:   func(string) (bool, string, error) { return true, targetDir, nil },
	}

	if err := command.run([]string{"alpha"}); err != nil {
		t.Fatalf("run returned error: %v", err)
	}

	content, err := os.ReadFile(filepath.Join(targetDir, "AGENTS.md"))
	if err != nil {
		t.Fatalf("failed to read deployed AGENTS.md: %v", err)
	}
	if string(content) != "project agents" {
		t.Fatalf("expected deployed AGENTS.md content, got %q", string(content))
	}
	if !strings.Contains(stdout.String(), "Deploy AGENTS.md from project?") {
		t.Fatalf("expected AGENTS prompt, got %q", stdout.String())
	}
	if stderr.Len() != 0 {
		t.Fatalf("expected empty stderr, got %q", stderr.String())
	}
}

func TestDeployRunReadsSkillAndAgentsSelectionsFromSameInput(t *testing.T) {
	repoRoot := makeContextRepo(t, []string{"alpha"})
	targetDir := t.TempDir()

	writeSkillFixture(t, filepath.Join(repoRoot, "utils", "skills"), "shared-only", "shared skill", true)

	agentsPath := filepath.Join(repoRoot, "projects", "alpha", "AGENTS.md")
	if err := os.WriteFile(agentsPath, []byte("project agents"), 0o644); err != nil {
		t.Fatalf("failed to create AGENTS.md: %v", err)
	}

	t.Setenv("CONTEXT_REPO", repoRoot)

	var stdout bytes.Buffer
	var stderr bytes.Buffer

	command := deployCommand{
		in:          strings.NewReader("1\ny\n"),
		out:         &stdout,
		errOut:      &stderr,
		locator:     filesystem.NewContextLocator(),
		getwd:       func() (string, error) { return targetDir, nil },
		interactive: func() bool { return true },
		inspector:   func(string) (bool, string, error) { return true, targetDir, nil },
	}

	if err := command.run([]string{"alpha"}); err != nil {
		t.Fatalf("run returned error: %v", err)
	}

	skillPath := filepath.Join(targetDir, ".codex", "skills", "shared-only", "SKILL.md")
	content, err := os.ReadFile(skillPath)
	if err != nil {
		t.Fatalf("failed to read deployed skill: %v", err)
	}
	if string(content) != "shared skill" {
		t.Fatalf("expected deployed skill content, got %q", string(content))
	}

	agentsContent, err := os.ReadFile(filepath.Join(targetDir, "AGENTS.md"))
	if err != nil {
		t.Fatalf("failed to read deployed AGENTS.md: %v", err)
	}
	if string(agentsContent) != "project agents" {
		t.Fatalf("expected deployed AGENTS.md content, got %q", string(agentsContent))
	}
	if stderr.Len() != 0 {
		t.Fatalf("expected empty stderr, got %q", stderr.String())
	}
}

func TestDeployRunSkipsMissingProjectAgentsWithMessage(t *testing.T) {
	repoRoot := makeContextRepo(t, []string{"alpha"})
	targetDir := t.TempDir()

	t.Setenv("CONTEXT_REPO", repoRoot)

	var stdout bytes.Buffer
	var stderr bytes.Buffer

	command := deployCommand{
		in:          strings.NewReader(""),
		out:         &stdout,
		errOut:      &stderr,
		locator:     filesystem.NewContextLocator(),
		getwd:       func() (string, error) { return targetDir, nil },
		interactive: func() bool { return true },
		inspector:   func(string) (bool, string, error) { return true, targetDir, nil },
	}

	if err := command.run([]string{"alpha"}); err != nil {
		t.Fatalf("run returned error: %v", err)
	}

	if _, err := os.Stat(filepath.Join(targetDir, "AGENTS.md")); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("expected AGENTS.md to be absent, got err=%v", err)
	}
	if !strings.Contains(stdout.String(), "AGENTS.md not found for project alpha. Skipping.") {
		t.Fatalf("expected skip message, got %q", stdout.String())
	}
	if stderr.Len() != 0 {
		t.Fatalf("expected empty stderr, got %q", stderr.String())
	}
}

func TestSelectProject(t *testing.T) {
	projects := []project.Project{{Name: "alpha"}, {Name: "beta"}}

	tests := []struct {
		name        string
		input       string
		projects    []project.Project
		wantName    string
		wantErrIs   error
		wantErrText string
	}{
		{
			name:     "selects valid index",
			input:    "2\n",
			projects: projects,
			wantName: "beta",
		},
		{
			name:      "fails when no projects",
			projects:  nil,
			wantErrIs: errs.ErrNoProjects,
		},
		{
			name:        "fails on invalid selection",
			input:       "0\n",
			projects:    projects,
			wantErrText: "invalid project selection",
		},
		{
			name:        "fails on non numeric selection",
			input:       "abc\n",
			projects:    projects,
			wantErrText: "invalid project selection",
		},
		{
			name:      "fails when selection missing",
			projects:  projects,
			wantErrIs: errs.ErrProjectSelectionMissing,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var out bytes.Buffer
			command := deployCommand{
				in:  strings.NewReader(tt.input),
				out: &out,
			}

			selected, err := command.selectProject(tt.projects)
			if tt.wantErrIs != nil && !errors.Is(err, tt.wantErrIs) {
				t.Fatalf("expected error %v, got %v", tt.wantErrIs, err)
			}
			if tt.wantErrText == "" && tt.wantErrIs == nil && err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if tt.wantErrText != "" {
				if err == nil || !strings.Contains(err.Error(), tt.wantErrText) {
					t.Fatalf("expected error containing %q, got %v", tt.wantErrText, err)
				}
			}
			if tt.wantName != "" && selected.Name != tt.wantName {
				t.Fatalf("expected project %q, got %q", tt.wantName, selected.Name)
			}
		})
	}
}

func TestSelectSkills(t *testing.T) {
	candidates := []skill.Candidate{
		{Name: "override", Source: skill.SourceProject},
		{Name: "shared-only", Source: skill.SourceShared},
	}

	tests := []struct {
		name        string
		input       string
		wantNames   []string
		wantErrIs   error
		wantErrText string
	}{
		{
			name:      "selects multiple skills once",
			input:     "2, 1, 2\n",
			wantNames: []string{"shared-only", "override"},
		},
		{
			name:      "fails on missing selection",
			input:     "\n",
			wantErrIs: errs.ErrSkillSelectionMissing,
		},
		{
			name:        "fails on invalid selection",
			input:       "3\n",
			wantErrText: "invalid skill selection",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var out bytes.Buffer
			command := deployCommand{
				in:  strings.NewReader(tt.input),
				out: &out,
			}

			selected, err := command.selectSkills(candidates)
			if tt.wantErrIs != nil && !errors.Is(err, tt.wantErrIs) {
				t.Fatalf("expected error %v, got %v", tt.wantErrIs, err)
			}
			if tt.wantErrText == "" && tt.wantErrIs == nil && err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if tt.wantErrText != "" {
				if err == nil || !strings.Contains(err.Error(), tt.wantErrText) {
					t.Fatalf("expected error containing %q, got %v", tt.wantErrText, err)
				}
				return
			}

			names := make([]string, 0, len(selected))
			for _, candidate := range selected {
				names = append(names, candidate.Name)
			}
			if strings.Join(names, ",") != strings.Join(tt.wantNames, ",") {
				t.Fatalf("expected names %v, got %v", tt.wantNames, names)
			}
		})
	}
}

func TestSelectAgents(t *testing.T) {
	agentsPath := filepath.Join(t.TempDir(), "AGENTS.md")
	if err := os.WriteFile(agentsPath, []byte("agents"), 0o644); err != nil {
		t.Fatalf("failed to create AGENTS.md fixture: %v", err)
	}

	tests := []struct {
		name     string
		input    string
		want     bool
		wantErr  string
		wantText string
	}{
		{
			name:  "accepts yes",
			input: "y\n",
			want:  true,
		},
		{
			name:  "accepts empty as no",
			input: "\n",
		},
		{
			name:    "rejects invalid answer",
			input:   "maybe\n",
			wantErr: "invalid AGENTS.md selection",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var out bytes.Buffer
			command := deployCommand{
				in:  strings.NewReader(tt.input),
				out: &out,
			}

			selected, err := command.selectAgents(&project.Project{Name: "alpha", AgentsPath: agentsPath})
			if tt.wantErr == "" && err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if tt.wantErr != "" {
				if err == nil || !strings.Contains(err.Error(), tt.wantErr) {
					t.Fatalf("expected error containing %q, got %v", tt.wantErr, err)
				}
				return
			}
			if selected != tt.want {
				t.Fatalf("expected %t, got %t", tt.want, selected)
			}
		})
	}
}

func TestSelectProjectScannerError(t *testing.T) {
	command := deployCommand{
		in:  errorReader{},
		out: &bytes.Buffer{},
	}

	_, err := command.selectProject([]project.Project{{Name: "alpha"}})
	if err == nil || !strings.Contains(err.Error(), "failed to read project selection") {
		t.Fatalf("expected scanner error, got %v", err)
	}
}

func TestInspectGitRepository(t *testing.T) {
	originalExecRunner := execRunner
	t.Cleanup(func() {
		execRunner = originalExecRunner
	})

	tests := []struct {
		name     string
		setupDir func(*testing.T) string
		setup    func(*testing.T)
		wantOK   bool
		wantRoot bool
		wantErr  string
	}{
		{
			name: "returns false for non git dir",
			setupDir: func(t *testing.T) string {
				return t.TempDir()
			},
		},
		{
			name: "returns root for git repo",
			setupDir: func(t *testing.T) string {
				dir := t.TempDir()
				cmd := exec.Command("git", "init")
				cmd.Dir = dir
				if output, err := cmd.CombinedOutput(); err != nil {
					t.Fatalf("git init failed: %v (%s)", err, string(output))
				}
				return dir
			},
			wantOK:   true,
			wantRoot: true,
		},
		{
			name: "returns command error for unexpected exec failure",
			setupDir: func(t *testing.T) string {
				return t.TempDir()
			},
			setup: func(t *testing.T) {
				execRunner = func(name string, args ...string) *exec.Cmd {
					return exec.Command(filepath.Join(t.TempDir(), "missing-git"), args...)
				}
			},
			wantErr: "no such file or directory",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			execRunner = originalExecRunner
			if tt.setup != nil {
				tt.setup(t)
			}
			dir := tt.setupDir(t)
			ok, root, err := inspectGitRepository(dir)
			if tt.wantErr == "" && err != nil {
				t.Fatalf("inspectGitRepository returned error: %v", err)
			}
			if tt.wantErr != "" {
				if err == nil || !strings.Contains(err.Error(), tt.wantErr) {
					t.Fatalf("expected error containing %q, got %v", tt.wantErr, err)
				}
				return
			}
			if ok != tt.wantOK {
				t.Fatalf("expected gitOK=%t, got %t", tt.wantOK, ok)
			}
			if tt.wantRoot {
				resolvedDir, resolveErr := filepath.EvalSymlinks(dir)
				if resolveErr != nil {
					t.Fatalf("failed to resolve dir: %v", resolveErr)
				}
				if root != resolvedDir {
					t.Fatalf("expected git root %q, got %q", resolvedDir, root)
				}
			}
		})
	}
}

func TestIsInteractiveStdin(t *testing.T) {
	originalStdinStat := stdinStat
	t.Cleanup(func() {
		stdinStat = originalStdinStat
	})

	tests := []struct {
		name string
		stat func() (os.FileInfo, error)
		want bool
	}{
		{
			name: "returns false on stat error",
			stat: func() (os.FileInfo, error) { return nil, errors.New("boom") },
			want: false,
		},
		{
			name: "returns false for non interactive input",
			stat: func() (os.FileInfo, error) { return fileInfoStub{mode: 0}, nil },
			want: false,
		},
		{
			name: "returns true for char device",
			stat: func() (os.FileInfo, error) { return fileInfoStub{mode: os.ModeCharDevice}, nil },
			want: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			stdinStat = tt.stat
			if got := isInteractiveStdin(); got != tt.want {
				t.Fatalf("expected %t, got %t", tt.want, got)
			}
		})
	}
}

type fileInfoStub struct {
	mode os.FileMode
}

type errorReader struct{}

func (errorReader) Read([]byte) (int, error) { return 0, errors.New("read failed") }

func (f fileInfoStub) Name() string       { return "" }
func (f fileInfoStub) Size() int64        { return 0 }
func (f fileInfoStub) Mode() os.FileMode  { return f.mode }
func (f fileInfoStub) ModTime() time.Time { return time.Time{} }
func (f fileInfoStub) IsDir() bool        { return false }
func (f fileInfoStub) Sys() any           { return nil }

func makeContextRepo(t *testing.T, projectNames []string) string {
	t.Helper()

	root := t.TempDir()
	for _, dir := range []string{"projects", "utils/skills", "cli/bin"} {
		if err := os.MkdirAll(filepath.Join(root, dir), 0o755); err != nil {
			t.Fatalf("failed to create %s: %v", dir, err)
		}
	}
	for _, name := range projectNames {
		if err := os.Mkdir(filepath.Join(root, "projects", name), 0o755); err != nil {
			t.Fatalf("failed to create project %s: %v", name, err)
		}
	}
	return root
}

func writeSkillFixture(t *testing.T, baseDir, name, skillContent string, withSkill bool) {
	t.Helper()

	skillDir := filepath.Join(baseDir, name)
	if err := os.MkdirAll(skillDir, 0o755); err != nil {
		t.Fatalf("failed to create skill dir %s: %v", skillDir, err)
	}
	if withSkill {
		if err := os.WriteFile(filepath.Join(skillDir, "SKILL.md"), []byte(skillContent), 0o644); err != nil {
			t.Fatalf("failed to create SKILL.md for %s: %v", name, err)
		}
	}
	if err := os.WriteFile(filepath.Join(skillDir, "README.md"), []byte("catalog"), 0o644); err != nil {
		t.Fatalf("failed to create README.md for %s: %v", name, err)
	}
}
