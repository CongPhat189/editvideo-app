import { StatusBar } from 'expo-status-bar';
import { use } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { MyUserContext } from '@/config/Contexts';

export default function Home() {
  const [user] = use(MyUserContext);

  return (
    <View style={styles.container}>
      <Text>hi {user?.full_name}</Text>
      <StatusBar style="auto" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
    alignItems: 'center',
    justifyContent: 'center',
  },
});