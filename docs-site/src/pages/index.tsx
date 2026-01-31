import type {ReactNode} from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import useBaseUrl from '@docusaurus/useBaseUrl';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';

import styles from './index.module.css';

function HeroSection() {
  return (
    <header className={clsx('hero hero--primary', styles.heroBanner)}>
      <div className="container">
        <Heading as="h1" className="hero__title">
          RepeatNoMore
        </Heading>
        <p className={styles.heroSkeptic}>
          "But ChatGPT can already answer questions..."
        </p>
        <p className="hero__subtitle">
          You're right. The problem isn't answering questions — AI solved that.<br/>
          The problem is <strong>keeping your knowledge base accurate and up-to-date</strong>.<br/>
          Nobody has time for that. And stale docs are worse than no docs.
        </p>
        <p className={styles.heroHighlight}>
          RepeatNoMore captures knowledge as a byproduct of answering questions — <br/>
          <strong>not as a separate chore nobody wants to do.</strong>
        </p>
        <div className={styles.buttons}>
          <Link
            className="button button--secondary button--lg"
            to="/docs/getting-started">
            Get Started →
          </Link>
          <Link
            className="button button--outline button--lg button--secondary"
            style={{marginLeft: '1rem'}}
            href="https://github.com/zskreisz/RepeatNoMore">
            ⭐ Star on GitHub
          </Link>
        </div>
        <p style={{marginTop: '2rem', fontSize: '1.1rem', opacity: 0.9}}>
          🆓 <strong>100% Open Source</strong> • Self-hosted • Your data stays yours
        </p>
      </div>
    </header>
  );
}

function ProblemSection() {
  const painImage = useBaseUrl('/img/pain_of_senior.png');
  return (
    <section className={clsx(styles.section, styles.painSection)}>
      <div className="container">
        <Heading as="h2" className={styles.sectionTitle}>
          📝 The Documentation Paradox
        </Heading>
        <div className={styles.paradoxQuote}>
          <blockquote>
            "Everybody wants to go to heaven, but nobody wants to die."
          </blockquote>
          <p className={styles.paradoxExplain}>
            <strong>Everybody loves getting their questions answered promptly.</strong><br/>
            <strong>Nobody wants to update the documentation.</strong>
          </p>
          <p className={styles.paradoxSolution}>
            Imagine questioning and <strong>updating</strong> your documentation in the same chat via Agentic AI.
          </p>
        </div>
        
        <div className={styles.painGrid}>
          <div className={styles.painImage}>
            <img 
              src={painImage} 
              alt="Senior developer frustrated by repeated questions" 
              style={{maxWidth: '100%', borderRadius: '12px'}}
            />
          </div>
          <div className={styles.painList}>
            <div className={styles.painItem}>
              <span className={styles.painEmoji}>🔄</span>
              <div>
                <strong>"We already discussed this last month..."</strong>
                <p>Important decisions get lost in chat history and emails</p>
              </div>
            </div>
            <div className={styles.painItem}>
              <span className={styles.painEmoji}>👋</span>
              <div>
                <strong>"The person who knew this left the company"</strong>
                <p>Critical knowledge walks out the door with every departure</p>
              </div>
            </div>
            <div className={styles.painItem}>
              <span className={styles.painEmoji}>⏰</span>
              <div>
                <strong>"I spend half my day answering the same questions"</strong>
                <p>Senior developers become expensive FAQ machines</p>
              </div>
            </div>
            <div className={styles.painItem}>
              <span className={styles.painEmoji}>🔍</span>
              <div>
                <strong>"I know this is documented somewhere..."</strong>
                <p>Information scattered across Slack, Confluence, emails, docs</p>
              </div>
            </div>
          </div>
        </div>

        <div className={styles.insightBox}>
          <p>
            AI can answer questions today. But it can only give <strong>good</strong> answers 
            if it works from <strong>maintained, accurate documentation</strong>. 
            That's the part nobody wants to do — until now.
          </p>
        </div>
      </div>
    </section>
  );
}

function HowItWorksSection() {
  return (
    <section className={styles.section}>
      <div className="container">
        <Heading as="h2" className={styles.sectionTitle}>
          ⚙️ How It Works
        </Heading>
        <p className={styles.sectionSubtitle}>
          Knowledge capture that happens automatically
        </p>
        
        <div className={styles.workflowSteps}>
          <div className={styles.workflowStep}>
            <div className={styles.stepNumber}>1</div>
            <div className={styles.stepContent}>
              <Heading as="h3">Someone asks a question</Heading>
              <p>Via Discord, Teams, or API — just like they would in Slack</p>
            </div>
          </div>
          <div className={styles.workflowStep}>
            <div className={styles.stepNumber}>2</div>
            <div className={styles.stepContent}>
              <Heading as="h3">AI answers from your knowledge base</Heading>
              <p>Searches your docs, finds relevant context, generates a helpful answer</p>
            </div>
          </div>
          <div className={styles.workflowStep}>
            <div className={styles.stepNumber}>3</div>
            <div className={styles.stepContent}>
              <Heading as="h3">Good answers get saved with one click</Heading>
              <p>Approve useful answers → they become part of your documentation</p>
              <p className={styles.stepAlt}>Not useful? Mark it → admins get notified to update the Q&A automatically</p>
              <p className={styles.stepAlt}>Want to improve the docs? Make a suggestion → it goes to the admin review channel for approval</p>
            </div>
          </div>
          <div className={styles.workflowStep}>
            <div className={styles.stepNumber}>4</div>
            <div className={styles.stepContent}>
              <Heading as="h3">Knowledge base grows automatically</Heading>
              <p>Version controlled, reviewed, searchable — without the documentation chore</p>
            </div>
          </div>
        </div>

        <p className={styles.workflowPunchline}>
          <strong>The result:</strong> Your documentation improves every time someone asks a question. 
          No separate "documentation day." No stale wikis. Just knowledge that grows naturally.
        </p>
      </div>
    </section>
  );
}

function OutcomesSection() {
  const outcomes = [
    {
      icon: '🚀',
      title: 'Faster Onboarding',
      description: 'New team members get answers instantly — no waiting for busy seniors.',
    },
    {
      icon: '⚡',
      title: 'Faster Development',
      description: 'Developers unblock themselves with accurate, up-to-date context.',
    },
    {
      icon: '🤖',
      title: 'Better AI Tools',
      description: 'Your AI coding assistants work from maintained knowledge, not stale docs.',
    },
    {
      icon: '📉',
      title: 'Zero Documentation Overhead',
      description: 'Knowledge is captured as work happens — not as a separate task.',
    },
  ];

  return (
    <section className={clsx(styles.section, styles.outcomesSection)}>
      <div className="container">
        <Heading as="h2" className={styles.sectionTitle}>
          📈 What Your Team Gets
        </Heading>
        <div className={styles.grid}>
          {outcomes.map((item, idx) => (
            <div key={idx} className={styles.card}>
              <div className={styles.cardIcon}>{item.icon}</div>
              <Heading as="h3">{item.title}</Heading>
              <p>{item.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function GetStartedSection() {
  return (
    <section className={clsx(styles.section, styles.getStartedSection)}>
      <div className="container">
        <Heading as="h2" className={styles.sectionTitle}>
          🚀 Get Started
        </Heading>
        <p className={styles.sectionSubtitle}>
          Up and running in 5 minutes
        </p>
        
        <div className={styles.setupCode}>
          <pre>
{`# Clone and configure
git clone https://github.com/zskreisz/RepeatNoMore
cd RepeatNoMore
cp .env.example .env

# Start with Docker
docker-compose up -d`}
          </pre>
        </div>
        
        <div className={styles.setupButtons}>
          <Link
            className="button button--primary button--lg"
            to="/docs/getting-started">
            📖 Full Setup Guide
          </Link>
          <Link
            className="button button--outline button--primary button--lg"
            href="https://github.com/zskreisz/RepeatNoMore/fork"
            style={{marginLeft: '1rem'}}>
            🍴 Fork & Customize
          </Link>
        </div>

        <div className={styles.openSourceBadges}>
          <div className={styles.osFeature}>
            <span>🔓</span>
            <strong>MIT License</strong>
          </div>
          <div className={styles.osFeature}>
            <span>🏠</span>
            <strong>Self-hosted</strong>
          </div>
          <div className={styles.osFeature}>
            <span>🔒</span>
            <strong>Your data stays yours</strong>
          </div>
          <div className={styles.osFeature}>
            <span>🛠️</span>
            <strong>Fully customizable</strong>
          </div>
        </div>
      </div>
    </section>
  );
}

export default function Home(): ReactNode {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title="Documentation That Maintains Itself"
      description="The problem isn't answering questions — AI solved that. The problem is keeping your knowledge base accurate. RepeatNoMore captures knowledge as a byproduct of daily work.">
      <HeroSection />
      <main>
        <ProblemSection />
        <HowItWorksSection />
        <OutcomesSection />
        <GetStartedSection />
      </main>
    </Layout>
  );
}
