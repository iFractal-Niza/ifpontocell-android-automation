# Git

## Fluxo padrão

```bash
# 1. Atualizar base
git checkout desenvolvimento && git pull origin desenvolvimento

# 2. Criar feature
git checkout -b feature/nome-da-feature

# 3. Trabalhar, commitar
git add .
git commit -m "feat: descrição da alteração"
git push -u origin feature/nome-da-feature

# 4. Atualizar com a base antes de integrar
git checkout desenvolvimento && git pull origin desenvolvimento
git checkout feature/nome-da-feature && git merge desenvolvimento

# 5. Integrar
git checkout desenvolvimento
git merge feature/nome-da-feature
git push origin desenvolvimento

# 6. Limpar
git branch -d feature/nome-da-feature
git push origin --delete feature/nome-da-feature
```

---

## Padrão de commits

| Prefixo | Quando usar |
|---|---|
| `feat` | algo novo |
| `fix` | correção de bug |
| `refactor` | reorganização sem mudar regra |
| `test` | adicionar ou ajustar testes |
| `chore` | config, gitignore, dependências |

---

## Checklist antes de merge

```bash
git status
make smoke
git diff desenvolvimento..feature/nome-da-feature
```

- [ ] Testes passaram
- [ ] Sem arquivo sensível (env.yaml, devices.yaml)
- [ ] Sem relatório ou cache versionado
- [ ] Sem código de debug
- [ ] Branch limpa

---

## Comandos úteis

```bash
git branch                                        # branch atual
git log --oneline --graph --decorate --all        # histórico visual
git log --oneline -5                              # últimos 5 commits
git diff desenvolvimento..feature/nome-da-feature # diferença entre branches
```

---

## Atalhos via Makefile

```bash
make smoke          # roda smoke antes de integrar
make merge-dev      # roda smoke e mescla na desenvolvimento
make merge-main     # roda smoke e mescla na main
make status         # git status
make commit m="feat: descrição"
make push
```