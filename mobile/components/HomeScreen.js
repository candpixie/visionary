import React from 'react';
import { StyleSheet, Text, View, TouchableOpacity, Image } from 'react-native';
import { StatusBar } from 'expo-status-bar';

export default function HomeScreen({ onNavigateToCamera }) {
  return (
    <View style={styles.container}>
      <StatusBar style="light" />
      
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>GLAUCOGUARD</Text>
        <Text style={styles.subtitle}>Detection System</Text>
      </View>

      {/* Main Content */}
      <View style={styles.content}>
        <View style={styles.iconContainer}>
          <Text style={styles.icon}>👁️</Text>
        </View>
        
        <Text style={styles.welcomeText}>Welcome</Text>
        <Text style={styles.description}>
          Connect your camera to start monitoring and detection
        </Text>
      </View>

      {/* Navigation Buttons */}
      <View style={styles.buttonContainer}>
        <TouchableOpacity 
          style={styles.primaryButton}
          onPress={onNavigateToCamera}
        >
          <Text style={styles.primaryButtonText}>Start Camera</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.secondaryButton}>
          <Text style={styles.secondaryButtonText}>Settings</Text>
        </TouchableOpacity>
      </View>

      {/* Footer */}
      <View style={styles.footer}>
        <Text style={styles.footerText}>Version 1.0.0</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#1a1a1a',
    paddingTop: 50,
  },
  header: {
    alignItems: 'center',
    paddingTop: 40,
    paddingBottom: 30,
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#00ff00',
    fontFamily: 'monospace',
    letterSpacing: 2,
  },
  subtitle: {
    fontSize: 16,
    color: '#888',
    marginTop: 5,
    fontFamily: 'monospace',
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 30,
  },
  iconContainer: {
    marginBottom: 30,
  },
  icon: {
    fontSize: 80,
  },
  welcomeText: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 15,
  },
  description: {
    fontSize: 16,
    color: '#aaa',
    textAlign: 'center',
    lineHeight: 24,
  },
  buttonContainer: {
    paddingHorizontal: 30,
    paddingBottom: 40,
  },
  primaryButton: {
    backgroundColor: '#00ff00',
    paddingVertical: 18,
    borderRadius: 10,
    alignItems: 'center',
    marginBottom: 15,
    shadowColor: '#00ff00',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 5,
  },
  primaryButtonText: {
    color: '#000',
    fontSize: 18,
    fontWeight: 'bold',
    fontFamily: 'monospace',
  },
  secondaryButton: {
    backgroundColor: '#333',
    paddingVertical: 18,
    borderRadius: 10,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#555',
  },
  secondaryButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  footer: {
    alignItems: 'center',
    paddingBottom: 20,
  },
  footerText: {
    color: '#666',
    fontSize: 12,
    fontFamily: 'monospace',
  },
});

