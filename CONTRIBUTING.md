# Contributing to Ledger Scrolls

First off, thank you for considering contributing to Ledger Scrolls! This project exists because of the Cardano community, and contributions from people like you make it better for everyone.

## 🌟 The BEACN Philosophy

Before contributing, please understand our core values:

- **For the people** — Tools should be accessible to everyone, not just the technically elite
- **Open source** — Knowledge and tools belong to the community
- **Decentralization** — No single point of control or failure
- **Permanence** — What we build should last

## 🤝 How Can I Contribute?

### Mint a Scroll (the contribution that matters most)

The most valuable thing you can add to this project is not code — it is a
scroll worth preserving. Every new scroll makes the library more real and
shows the next person what this technology is for.

### Creating & Sharing Scrolls

Anyone can mint their own scroll — you don't need to be a developer. Start with
the **[Your First Scroll quickstart](docs/YOUR_FIRST_SCROLL.md)**: pick a format
(a Standard Scroll for tiny files, a **Chain Scroll** for anything larger), optimize the
file, mint, verify from chain, and register it.

Minted something cool? Share it!

- Add a registry entry (pointer + required `sha256`) and open a PR
- Document it in `examples/` with your `receipts.json`
- Share on social media with **#LedgerScrolls** and tag
  [@BEACNpool](https://x.com/BEACNpool)

### Reporting Bugs

Found something broken? [Open an issue](https://github.com/BEACNpool/ledger-scrolls/issues/new) with:

- A clear title and description
- Steps to reproduce the problem
- Expected vs actual behavior
- Browser/OS/environment details
- Screenshots if applicable

### Suggesting Features

Have an idea? [Start a discussion](https://github.com/BEACNpool/ledger-scrolls/discussions) or open an issue:

- Describe the feature clearly
- Explain why it would be valuable
- Consider how it aligns with our philosophy

### Code Contributions

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-thing`)
3. **Make your changes**
4. **Test thoroughly**
5. **Commit with clear messages** (`git commit -m "Add amazing thing that does X"`)
6. **Push to your fork** (`git push origin feature/amazing-thing`)
7. **Open a Pull Request**

### Documentation

Good documentation is crucial! You can help by:

- Fixing typos and clarifying language
- Adding examples
- Translating to other languages
- Writing tutorials

## 📝 Code Style

### JavaScript

- Use `const` and `let`, not `var`
- Use template literals for string interpolation
- Descriptive variable names
- Comment complex logic

### Bash Scripts

- Use `set -e` for error handling
- Include usage information
- Add colors for better UX
- Test on Linux (primary target)

### Documentation

- Use clear, simple language
- Include examples
- Keep formatting consistent
- Update the table of contents

## 🧪 Testing

Before submitting:

1. **Run the conformance suite** — `python3 conformance/run_conformance.py`
   and `node conformance/run_conformance.mjs` must both pass. This is the
   protocol's contract; changes to reading/writing behavior need a fixture.
2. **Test the viewer** — Open `index.html` in multiple browsers
3. **Test scripts** — Run on a testnet first if possible
4. **Check responsiveness** — Test on mobile viewports
5. **Verify links** — All documentation links should work

## 📋 Pull Request Process

1. Update documentation if needed
2. Add yourself to contributors if you'd like
3. Ensure CI passes (if configured)
4. Request review from maintainers
5. Address feedback promptly

## 🎨 Design Principles

When contributing to the UI:

- **Accessible** — Consider screen readers and keyboard navigation
- **Responsive** — Works on all screen sizes
- **Beautiful** — Maintain the cosmic/ethereal aesthetic
- **Fast** — Don't add unnecessary dependencies

## 🚫 What We Don't Accept

- Features that compromise security
- Code that centralizes control
- Changes that break existing scrolls
- Anything that violates the MIT license

## 💬 Communication

- **GitHub Issues** — Bug reports and feature requests
- **GitHub Discussions** — General questions and ideas
- **Twitter/X** — [@BEACNpool](https://x.com/BEACNpool)

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

## 🙏 Thank You

Every contribution, no matter how small, helps preserve knowledge for future generations. You're part of something bigger than code — you're helping build a library that cannot burn.

*Welcome to the eternal archive.*
