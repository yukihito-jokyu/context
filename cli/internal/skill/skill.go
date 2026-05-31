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
	for _, candidate := range candidates {
		for _, base := range []string{".claude/skills", ".codex/skills"} {
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
		}
	}
	return nil
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
