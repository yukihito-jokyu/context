package skill

import (
	"io"
	"os"
	"path/filepath"
	"sort"

	"github.com/yukihito-jokyu/context/cli/internal/errs"
)

const (
	SourceProject = "project"
	SourceShared  = "utils"
)

type Candidate struct {
	Name       string
	Source     string
	SourcePath string
}

type Deployment struct {
	Candidate Candidate
	Targets   []string
}

type TargetResult struct {
	Candidate Candidate
	Target    string
	Err       error
}

var agentSkillBases = []string{".claude/skills", ".codex/skills"}

func Collect(sharedDir, projectDir string) ([]Candidate, error) {
	shared, err := collectFromDir(sharedDir, SourceShared)
	if err != nil {
		return nil, err
	}
	project, err := collectFromDir(projectDir, SourceProject)
	if err != nil {
		return nil, err
	}

	merged := make(map[string]Candidate, len(shared)+len(project))
	for _, candidate := range shared {
		merged[candidate.Name] = candidate
	}
	for _, candidate := range project {
		merged[candidate.Name] = candidate
	}

	names := make([]string, 0, len(merged))
	for name := range merged {
		names = append(names, name)
	}
	sort.Strings(names)

	candidates := make([]Candidate, 0, len(names))
	for _, name := range names {
		candidates = append(candidates, merged[name])
	}
	return candidates, nil
}

func DeployToAgents(targetDir string, candidates []Candidate) error {
	deployments := make([]Deployment, 0, len(candidates))
	for _, candidate := range candidates {
		deployments = append(deployments, Deployment{
			Candidate: candidate,
			Targets:   agentSkillBases,
		})
	}
	return Deploy(targetDir, deployments)
}

func Deploy(targetDir string, deployments []Deployment) error {
	results := DeployWithReport(targetDir, deployments)
	for _, result := range results {
		if result.Err != nil {
			return result.Err
		}
	}
	return nil
}

func DeployWithReport(targetDir string, deployments []Deployment) []TargetResult {
	results := make([]TargetResult, 0)
	for _, deployment := range deployments {
		for _, base := range deployment.Targets {
			err := deployTarget(targetDir, deployment.Candidate, base)
			results = append(results, TargetResult{
				Candidate: deployment.Candidate,
				Target:    base,
				Err:       err,
			})
		}
	}
	return results
}

func ExistingAgentTargets(targetDir string, candidate Candidate) ([]string, error) {
	existing := make([]string, 0, len(agentSkillBases))
	for _, base := range agentSkillBases {
		dstDir := filepath.Join(targetDir, base, candidate.Name)
		_, err := os.Stat(dstDir)
		if err == nil {
			existing = append(existing, base)
			continue
		}
		if os.IsNotExist(err) {
			continue
		}
		return nil, errs.Wrap("failed to stat skill dir", dstDir, err)
	}
	return existing, nil
}

func MissingAgentTargets(targetDir string, candidate Candidate) ([]string, error) {
	existing, err := ExistingAgentTargets(targetDir, candidate)
	if err != nil {
		return nil, err
	}

	existingSet := make(map[string]struct{}, len(existing))
	for _, base := range existing {
		existingSet[base] = struct{}{}
	}

	missing := make([]string, 0, len(agentSkillBases))
	for _, base := range agentSkillBases {
		if _, ok := existingSet[base]; ok {
			continue
		}
		missing = append(missing, base)
	}
	return missing, nil
}

func ExistsInAgents(targetDir string, candidate Candidate) (bool, error) {
	existing, err := ExistingAgentTargets(targetDir, candidate)
	if err != nil {
		return false, err
	}
	return len(existing) > 0, nil
}

func collectFromDir(root, source string) ([]Candidate, error) {
	entries, err := os.ReadDir(root)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, errs.Wrap("failed to read skills dir", root, err)
	}

	candidates := make([]Candidate, 0, len(entries))
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}

		skillDir := filepath.Join(root, entry.Name())
		info, err := os.Stat(filepath.Join(skillDir, "SKILL.md"))
		if err != nil {
			if os.IsNotExist(err) {
				continue
			}
			return nil, errs.Wrap("failed to stat skill file", skillDir, err)
		}
		if info.IsDir() {
			continue
		}

		candidates = append(candidates, Candidate{
			Name:       entry.Name(),
			Source:     source,
			SourcePath: skillDir,
		})
	}
	return candidates, nil
}

func copyFile(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return errs.Wrap("failed to open skill file", src, err)
	}
	defer in.Close()

	out, err := os.Create(dst)
	if err != nil {
		return errs.Wrap("failed to create skill file", dst, err)
	}

	if _, err := io.Copy(out, in); err != nil {
		out.Close()
		return errs.Wrap("failed to copy skill file", dst, err)
	}
	if err := out.Close(); err != nil {
		return errs.Wrap("failed to close skill file", dst, err)
	}
	return nil
}

func deployTarget(targetDir string, candidate Candidate, base string) error {
	dstDir := filepath.Join(targetDir, base, candidate.Name)
	if err := os.RemoveAll(dstDir); err != nil {
		return errs.Wrap("failed to reset skill dir", dstDir, err)
	}
	if err := os.MkdirAll(dstDir, 0o755); err != nil {
		return errs.Wrap("failed to create skill dir", dstDir, err)
	}

	srcFile := filepath.Join(candidate.SourcePath, "SKILL.md")
	dstFile := filepath.Join(dstDir, "SKILL.md")
	if err := copyFile(srcFile, dstFile); err != nil {
		return err
	}
	return nil
}
