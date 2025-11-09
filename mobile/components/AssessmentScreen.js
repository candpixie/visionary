import React, { useState } from 'react';
import { StyleSheet, Text, View, TouchableOpacity, Image, ScrollView } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { LinearGradient } from 'expo-linear-gradient';

export default function AssessmentScreen({ onComplete, onBack }) {
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState({});

  const questions = [
    {
      id: 1,
      question: "Have you been diagnosed with any vision-related conditions?",
      options: [
        "Yes, I have been diagnosed with a vision condition",
        "No, I have not been diagnosed",
        "I'm not sure / I'm waiting for diagnosis",
        "I prefer not to answer"
      ]
    },
    {
      id: 2,
      question: "How would you describe your overall vision clarity?",
      options: [
        "Excellent - very clear",
        "Good - mostly clear with minor issues",
        "Fair - noticeable blurriness or distortion",
        "Poor - significant vision impairment"
      ]
    },
    {
      id: 3,
      question: "How would you describe your peripheral (side) vision?",
      options: [
        "Excellent - no issues",
        "Good - minor limitations",
        "Fair - noticeable limitations",
        "Poor - significant limitations"
      ]
    },
    {
      id: 4,
      question: "How is your vision in low light or at night?",
      options: [
        "Excellent - no issues",
        "Good - minor difficulty",
        "Fair - noticeable difficulty",
        "Poor - very difficult to see"
      ]
    },
    {
      id: 5,
      question: "What challenges do you face in daily navigation?",
      options: [
        "No significant challenges",
        "Occasional difficulty with obstacles",
        "Frequent difficulty with navigation",
        "Severe difficulty requiring assistance"
      ]
    },
    {
      id: 6,
      question: "How often do you experience vision-related difficulties?",
      options: [
        "Rarely or never",
        "Occasionally (a few times a week)",
        "Frequently (daily or multiple times per day)",
        "Constantly"
      ]
    },
    {
      id: 7,
      question: "What is your primary goal with Visionary?",
      options: [
        "Early detection and prevention",
        "Monitor existing vision condition",
        "Improve daily navigation safety",
        "Track vision changes over time"
      ]
    },
    {
      id: 8,
      question: "How has vision loss affected your daily activities?",
      options: [
        "No significant impact",
        "Minor impact on some activities",
        "Moderate impact on many activities",
        "Severe impact requiring assistance"
      ]
    }
  ];

  const handleAnswer = (answer) => {
    const newAnswers = { ...answers };
    newAnswers[currentQuestion] = answer;
    setAnswers(newAnswers);

    // Move to next question or complete
    if (currentQuestion < questions.length - 1) {
      setCurrentQuestion(currentQuestion + 1);
    } else {
      // All questions answered
      handleComplete(newAnswers);
    }
  };

  const handleComplete = (finalAnswers) => {
    console.log('Assessment completed:', finalAnswers);
    if (onComplete) {
      onComplete(finalAnswers);
    }
  };

  const handlePrevious = () => {
    if (currentQuestion > 0) {
      setCurrentQuestion(currentQuestion - 1);
    }
  };

  const currentQ = questions[currentQuestion];
  const progress = ((currentQuestion + 1) / questions.length) * 100;

  return (
    <LinearGradient
      colors={['#000000', '#001919', '#004D4D', '#000000']}
      locations={[0, 0.3, 0.7, 1]}
      style={styles.container}
    >
      <StatusBar style="light" />
      
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={onBack} style={styles.backButton}>
          <Text style={styles.backButtonText}>← Back</Text>
        </TouchableOpacity>
        <View style={styles.headerCenter}>
          <Image 
            source={require('../assets/logo.png')} 
            style={styles.logo}
            resizeMode="contain"
          />
          <Text style={styles.title}>Assessment</Text>
        </View>
        <View style={styles.placeholder} />
      </View>

      {/* Progress Bar */}
      <View style={styles.progressContainer}>
        <View style={styles.progressBar}>
          <View style={[styles.progressFill, { width: `${progress}%` }]} />
        </View>
        <Text style={styles.progressText}>
          Question {currentQuestion + 1} of {questions.length}
        </Text>
      </View>

      {/* Content */}
      <ScrollView style={styles.content} contentContainerStyle={styles.contentContainer}>
        <View style={styles.questionContainer}>
          <Text style={styles.questionText}>{currentQ.question}</Text>
        </View>

        <View style={styles.optionsContainer}>
          {currentQ.options.map((option, index) => (
            <TouchableOpacity
              key={index}
              style={[
                styles.optionButton,
                answers[currentQuestion] === option && styles.optionButtonSelected
              ]}
              onPress={() => handleAnswer(option)}
            >
              <Text style={[
                styles.optionText,
                answers[currentQuestion] === option && styles.optionTextSelected
              ]}>
                {option}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Navigation Buttons */}
        <View style={styles.navigationContainer}>
          {currentQuestion > 0 && (
            <TouchableOpacity style={styles.prevButton} onPress={handlePrevious}>
              <Text style={styles.prevButtonText}>Previous</Text>
            </TouchableOpacity>
          )}
        </View>
      </ScrollView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingTop: 50,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 20,
  },
  backButton: {
    padding: 10,
  },
  backButtonText: {
    color: '#00CED1',
    fontSize: 16,
    fontFamily: 'monospace',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
    fontFamily: 'monospace',
  },
  placeholder: {
    width: 60,
  },
  headerCenter: {
    alignItems: 'center',
    flex: 1,
  },
  logo: {
    width: 50,
    height: 50,
    marginBottom: 10,
  },
  progressContainer: {
    paddingHorizontal: 30,
    paddingBottom: 20,
  },
  progressBar: {
    height: 6,
    backgroundColor: '#1a1a2e',
    borderRadius: 3,
    marginBottom: 10,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#00CED1',
    borderRadius: 3,
  },
  progressText: {
    color: '#888',
    fontSize: 12,
    textAlign: 'center',
    fontFamily: 'monospace',
  },
  content: {
    flex: 1,
  },
  contentContainer: {
    paddingHorizontal: 30,
    paddingBottom: 40,
  },
  questionContainer: {
    marginBottom: 30,
  },
  questionText: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#fff',
    textAlign: 'center',
    lineHeight: 32,
    fontFamily: 'monospace',
  },
  optionsContainer: {
    marginBottom: 30,
  },
  optionButton: {
    backgroundColor: '#1a1a2e',
    padding: 18,
    borderRadius: 10,
    marginBottom: 15,
    borderWidth: 2,
    borderColor: '#004D4D',
  },
  optionButtonSelected: {
    backgroundColor: '#004D4D',
    borderColor: '#00CED1',
    shadowColor: '#00CED1',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 5,
  },
  optionText: {
    color: '#aaa',
    fontSize: 16,
    textAlign: 'center',
    lineHeight: 24,
    fontFamily: 'monospace',
  },
  optionTextSelected: {
    color: '#00CED1',
    fontWeight: 'bold',
    fontFamily: 'monospace',
  },
  navigationContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: 20,
  },
  prevButton: {
    backgroundColor: '#333',
    paddingVertical: 12,
    paddingHorizontal: 30,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#555',
  },
  prevButtonText: {
    color: '#fff',
    fontSize: 16,
    fontFamily: 'monospace',
  },
});
