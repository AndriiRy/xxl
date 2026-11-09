#pragma once
#include <string>
#include <cstdlib>
#define LOW 0
#define HIGH 1
#define INPUT_PULLUP 2
#define OUTPUT 1
inline void pinMode(int,int){} inline void digitalWrite(int,int){} inline int digitalRead(int){return 1;}
template<class T> T min(T a,T b){return a<b?a:b;}
struct String{ std::string s; String(const char*c=""):s(c){} String(std::string x):s(x){}
 int length(){return s.size();} char charAt(int i){return s[i];} String substring(int a,int b=-1){return b<0?s.substr(a):s.substr(a,b-a);}
 void trim(){} int indexOf(char c){return s.find(c);} long toInt(){return atol(s.c_str());}};
struct S{ void begin(long){} int available(){return 0;} String readStringUntil(char){return "";}
 template<class T> void print(T){} template<class T> void println(T){} void println(){}} Serial;
#define A0 14
#define A1 15
#define A2 16
#define A3 17
