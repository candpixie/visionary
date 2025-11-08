import { useState } from 'react';
import { LandingPage } from './components/LandingPage';
import { SignInPage } from './components/SignInPage';
import { SignUpPage } from './components/SignUpPage';
import { QuestionnairePage } from './components/QuestionnairePage';
import { DashboardPage } from './components/DashboardPage';
import { CameraConnectionPage } from './components/CameraConnectionPage';

type Page = 'landing' | 'signin' | 'signup' | 'questionnaire' | 'dashboard' | 'camera';

export default function App() {
  const [currentPage, setCurrentPage] = useState<Page>('landing');
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const handleNavigate = (page: Page) => {
    setCurrentPage(page);
  };

  const handleSignIn = () => {
    setIsAuthenticated(true);
    setCurrentPage('questionnaire');
  };

  const handleSignUp = () => {
    setIsAuthenticated(true);
    setCurrentPage('questionnaire');
  };

  const handleQuestionnaireComplete = () => {
    setCurrentPage('dashboard');
  };

  const handleSignOut = () => {
    setIsAuthenticated(false);
    setCurrentPage('landing');
  };

  return (
    <div className="min-h-screen">
      {currentPage === 'landing' && (
        <LandingPage onNavigate={handleNavigate} />
      )}
      {currentPage === 'signin' && (
        <SignInPage 
          onNavigate={handleNavigate} 
          onSignIn={handleSignIn}
        />
      )}
      {currentPage === 'signup' && (
        <SignUpPage 
          onNavigate={handleNavigate}
          onSignUp={handleSignUp}
        />
      )}
      {currentPage === 'questionnaire' && (
        <QuestionnairePage 
          onComplete={handleQuestionnaireComplete}
        />
      )}
      {currentPage === 'dashboard' && (
        <DashboardPage 
          onSignOut={handleSignOut}
          onNavigate={handleNavigate}
        />
      )}
      {currentPage === 'camera' && (
        <CameraConnectionPage 
          onBack={() => setCurrentPage('dashboard')}
        />
      )}
    </div>
  );
}