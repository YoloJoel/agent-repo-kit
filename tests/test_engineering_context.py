"""REQ-CONTEXTUAL-001: initialization observes project facts without inventing a system."""

from agent_repo_kit import core as kit
from test_workflows import RepositoryCase


class EngineeringContextTests(RepositoryCase):
    def test_empty_project_keeps_business_architecture_and_stack_unknown(self):
        self.initialize()
        profile = kit.read_json(self.root / '.ai/project.json')
        self.assertEqual(profile['languages'], [])
        context = (self.root / 'docs/project-context.md').read_text()
        self.assertIn('Not established', context)
        self.assertFalse((self.root / 'docs/architecture/overview.md').exists())
        self.assertFalse((self.root / 'openspec/specs').exists())

    def test_mixed_repository_records_declared_versions_and_preserves_human_context(self):
        self.write('pom.xml', '<project xmlns="http://maven.apache.org/POM/4.0.0"><properties><java.version>21</java.version></properties><parent><artifactId>spring-boot-starter-parent</artifactId><version>4.1.0</version></parent></project>')
        self.write('src/main/java/App.java', 'class App {}\n')
        self.write('native/module.c', 'int value(void) { return 7; }\n')
        self.write('src/test/java/AppTest.java', 'class AppTest {}\n')
        self.write('docs/project-context.md', '# Existing human context\nKeep accepted boundaries.\n')
        self.initialize('existing')
        profile = kit.read_json(self.root / '.ai/project.json')
        self.assertEqual(profile['languages'], ['C', 'Java'])
        self.assertEqual(profile['declared_versions']['pom.xml:java.version'], '21')
        self.assertEqual(profile['declared_versions']['pom.xml:parent:spring-boot-starter-parent'], '4.1.0')
        self.assertEqual(profile['test_roots'], ['src/test'])
        self.assertIn('C, Java', (self.root / 'AGENTS.md').read_text())
        self.assertEqual((self.root / 'docs/project-context.md').read_text(), '# Existing human context\nKeep accepted boundaries.\n')
        self.assertEqual(kit.init_repo(self.root)['changed'], [])

    def test_invalid_build_file_is_an_explicit_gap_and_never_a_passing_command(self):
        self.write('pom.xml', '<project>unfinished')
        self.initialize('existing')
        profile = kit.read_json(self.root / '.ai/project.json')
        self.assertIn('Could not parse build facts: pom.xml', profile['unknowns'])
        self.assertEqual(kit.policy_at(self.root)['checks'], [])

    def test_existing_context_and_standard_can_be_mapped_without_duplicate_documents(self):
        p = kit.default_policy('existing', ['codex'])
        p['paths'].update(context='manual/context.md', standard='manual/rules.md')
        self.write(kit.POLICY, kit.dump(p))
        self.write('manual/context.md', '# Accepted project context\n')
        self.write('manual/rules.md', '# Human engineering rules\n')
        self.write('app.py', 'value = 7\n')
        kit.init_repo(self.root)
        self.assertFalse((self.root / 'docs/project-context.md').exists())
        self.assertFalse((self.root / 'docs/engineering-standard.md').exists())
        self.assertIn('manual/context.md', (self.root / 'AGENTS.md').read_text())
        self.assertIn('manual/rules.md', (self.root / 'AGENTS.md').read_text())
        self.assertEqual((self.root / 'manual/rules.md').read_text(), '# Human engineering rules\n')


if __name__ == '__main__':
    import unittest
    unittest.main()
