/**
 * Parse 4-space indented markdown into a tree structure.
 * Each level uses "- " prefix with 4 spaces per indent.
 */
export interface TreeNode {
  text: string
  level: number
  path: string
  children: TreeNode[]
}

export function parseMarkdownToTree(md: string): TreeNode {
  const lines = md.split('\n').filter(line => line.trim().startsWith('-'))
  const root: TreeNode = { text: '测试设计', level: 0, path: '0', children: [] }

  const stack: TreeNode[] = [root]
  let counter = 0

  for (const line of lines) {
    const trimmed = line.trimStart()
    // Count leading spaces (each level = 4 spaces)
    const indent = line.length - trimmed.length
    const level = Math.floor(indent / 4) + 1
    const text = trimmed.replace(/^-\s*/, '')

    if (!text) continue

    counter++
    const path = String(counter)
    const node: TreeNode = { text, level, path, children: [] }

    // Find parent: pop stack until we find a node with level < current
    while (stack.length > 1 && stack[stack.length - 1].level >= level) {
      stack.pop()
    }

    stack[stack.length - 1].children.push(node)
    stack.push(node)
  }

  return root
}

/**
 * Convert TreeNode to markmap-compatible data format.
 */
export function treeToMarkmap(node: TreeNode): any {
  if (node.children.length === 0) {
    return node.text
  }
  const result: any = {}
  for (const child of node.children) {
    result[child.text] = treeToMarkmap(child)
  }
  return result
}

/**
 * Convert TreeNode back to markdown string.
 */
export function treeToMarkdown(node: TreeNode, indent: number = 0): string {
  const lines: string[] = []
  if (node.level > 0) {
    lines.push(' '.repeat((indent - 1) * 4) + `- ${node.text}`)
  }
  for (const child of node.children) {
    lines.push(treeToMarkdown(child, indent + 1))
  }
  return lines.join('\n')
}
