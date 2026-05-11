import type {ReactNode} from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import CodeBlock from '@theme/CodeBlock';

import styles from './index.module.css';

const QUICKSTART = `from fastmcp import FastMCP
from bank2ai import register_tools

app = FastMCP("my-bank")

# Every handler is optional, pass only the tools you've implemented.
register_tools(
    app,
    get_accounts=...,
    get_categories=...,
    # get_transactions=..., get_transaction=..., get_transactions_summary=...,
    # get_recipients=..., create_recipient=...,
    # prepare_transfer=..., execute_transfer=...,
)
`;

type Feature = {
  title: string;
  description: string;
  href: string;
  cta: string;
};

const FEATURES: Feature[] = [
  {
    title: 'A shared banking vocabulary',
    description:
      'Standard banking MCP tools (accounts, transactions, categories, spending summaries, recipients, transfers) with fixed input/output schemas. Implement them once, get every bank2ai client for free.',
    href: '/docs/specification/overview',
    cta: 'Read the spec →',
  },
  {
    title: 'A Python library to wire it up',
    description:
      'The bank2ai package ships shared Pydantic models and a register_tools helper on top of FastMCP. Plug in async handlers backed by your bank APIs; the protocol layer is done.',
    href: '/docs/library/overview',
    cta: 'Use the library →',
  },
  {
    title: 'A marketplace of servers and skills',
    description:
      'Compliant servers and the agent skills built on top are distributed as a Claude Code plugin marketplace, so any compatible client can install a bank or skill in one command.',
    href: '/docs/marketplace/overview',
    cta: 'Browse the marketplace →',
  },
];

function Hero() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <header className={clsx('hero', styles.heroBanner)}>
      <div className="container">
        <img
          src="/img/logo.svg"
          alt="bank2ai"
          className={clsx(styles.heroLogo, styles.heroLogoLight)}
        />
        <img
          src="/img/logo-dark.svg"
          alt="bank2ai"
          className={clsx(styles.heroLogo, styles.heroLogoDark)}
        />
        <p className={styles.heroSubtitle}>{siteConfig.tagline}</p>
        <p className={styles.heroLede}>
          Bank2ai is the open standard that lets banks, fintechs, and AI builders share a single
          banking vocabulary instead of reinventing one, exposed over the{' '}
          <a href="https://modelcontextprotocol.io">Model Context Protocol</a>.
        </p>
        <div className={styles.heroButtons}>
          <Link
            className="button button--primary button--lg"
            to="/docs/getting-started/quickstart">
            Quickstart
          </Link>
          <Link
            className="button button--secondary button--lg"
            to="/docs/specification/overview">
            Read the spec
          </Link>
        </div>
      </div>
    </header>
  );
}

function FeatureGrid() {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FEATURES.map((feature) => (
            <div key={feature.title} className={clsx('col col--4', styles.featureCol)}>
              <div className={styles.featureCard}>
                <Heading as="h3">{feature.title}</Heading>
                <p>{feature.description}</p>
                <Link to={feature.href}>{feature.cta}</Link>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Quickstart() {
  return (
    <section className={styles.quickstart}>
      <div className="container">
        <div className="row">
          <div className="col col--5">
            <Heading as="h2">A bank server in ten lines</Heading>
            <p>
              Install <code>bank2ai</code>, supply async handlers for your backend, and{' '}
              <code>register_tools</code> wires the full bank2ai surface onto a FastMCP app.
            </p>
            <Link className="button button--primary" to="/docs/getting-started/quickstart">
              Full quickstart →
            </Link>
          </div>
          <div className="col col--7">
            <CodeBlock language="python">{QUICKSTART}</CodeBlock>
          </div>
        </div>
      </div>
    </section>
  );
}

function BanconyStrip() {
  return (
    <section className={styles.bancony}>
      <div className="container">
        <Heading as="h2">Stewarded by Bancony</Heading>
        <p>
          Bank2ai is an open standard, freely usable by any bank or fintech. Its development is
          stewarded by <a href="https://bancony.com">Bancony</a>, which builds enterprise-ready MCP
          servers, an SDK, an in-channel chat agent (with Generative UI and RAG), and advisory
          agents on top of the bank2ai surface.
        </p>
        <div className={styles.heroButtons}>
          <Link className="button button--primary" to="/docs/enterprise/overview">
            Enterprise offerings
          </Link>
          <Link
            className="button button--secondary"
            href="https://bancony.com">
            Visit bancony.com
          </Link>
        </div>
      </div>
    </section>
  );
}

export default function Home(): ReactNode {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title={siteConfig.title}
      description={siteConfig.tagline}>
      <Hero />
      <main>
        <FeatureGrid />
        <Quickstart />
        <BanconyStrip />
      </main>
    </Layout>
  );
}
