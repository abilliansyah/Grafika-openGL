#include <glad/glad.h>
#include <GLFW/glfw3.h>
#include <cmath>
#include <cstdio>

#define PI 3.14159265358979f

// ─── State & Helpers ──────────────────────────────────────────────────────
int winW = 1200, winH = 800, moonSides = 6;
float zoom = 1.f, moonAngle = 0.8f, orbitRadius = 0.28f, t = 0.f, speedMult = 1.f;
bool paused = false, dragging = false;
const float SUN_X = 0.55f;

struct Star { float x, y, r, bri, spd, ph, cr, cg, cb; } stars[600];
float rng() { static float s=42.f; s=sinf(s)*10000.f; return s-floorf(s); }
float asp() { return (float)winW / winH; }
float mx()  { return (cosf(moonAngle) * orbitRadius * zoom) / asp(); }
float my()  { return sinf(moonAngle) * orbitRadius * zoom; }

// ─── Core Renderer (DRY) ──────────────────────────────────────────────────
void shape(int mode, float x, float y, float rx, float ry, int seg, float rot=0) {
    glBegin(mode);
    if(mode == GL_TRIANGLE_FAN) glVertex2f(x, y);
    for(int i=0; i <= (mode==GL_LINE_LOOP ? seg-1 : seg); i++) {
        float a = 2.f*PI*i/seg + rot;
        glVertex2f(x + cosf(a)*rx/asp(), y + sinf(a)*ry);
    }
    glEnd();
}

void glow(float x, float y, float r, float R, float G, float B, int lyrs) {
    glBlendFunc(GL_SRC_ALPHA, GL_ONE);
    for(int i=1; i<=lyrs; i++) {
        glBegin(GL_TRIANGLE_FAN);
        glColor4f(R,G,B,0.07f/i); glVertex2f(x,y);
        glColor4f(R,G,B,0.f);
        for(int j=0; j<=40; j++) {
            float a = 2.f*PI*j/40, sc = 1.f+i*0.5f;
            glVertex2f(x + cosf(a)*r*sc/asp(), y + sinf(a)*r*sc);
        }
        glEnd();
    }
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
}

// ─── World Elements ───────────────────────────────
void drawWorld(float sx, float sy, float ex, float ey, float a, float rz, float mz) {
    // Background & Stars
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    glBegin(GL_QUADS);
    glColor3f(0.01f, 0.f, 0.04f); glVertex2f(-1,-1); glVertex2f(1,-1);
    glColor3f(0.03f, 0.01f, 0.1f); glVertex2f(1,1); glVertex2f(-1,1); glEnd();
    
    glBlendFunc(GL_SRC_ALPHA, GL_ONE);
    glBegin(GL_POINTS);
    for(auto& s : stars) {
        glPointSize(s.r * winH);
        glColor4f(s.cr, s.cg, s.cb, s.bri * (0.6f + 0.4f * sinf(t*s.spd + s.ph)));
        glVertex2f(s.x, s.y);
    } glEnd();

    // Orbit Line
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    glLineWidth(0.8f); glBegin(GL_LINE_LOOP);
    for(int i=0; i<100; i++) {
        float ang = 2.f*PI*i/100, diff = fabsf(ang - moonAngle);
        if(diff > PI) diff = 2.f*PI - diff;
        glColor4f(0.6f, 0.75f, 1.f, 0.05f + 0.12f*(1.f - diff/PI));
        glVertex2f(ex + cosf(ang)*orbitRadius*zoom/a, ey + sinf(ang)*orbitRadius*zoom);
    } glEnd();

    // Sun
    float sr = 0.13f * zoom;
    glow(sx, sy, sr, 1.f, 0.6f, 0.15f, 5);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE);
    glBegin(GL_TRIANGLES); // Batched Draw Call
    for(int i=0; i<16; i++) {
        float ang = 2.f*PI*i/16 + t*0.12f, len = sr*(1.3f+0.15f*sinf(t*1.2f+i*0.8f)), wid = 0.06f+0.02f*sinf(t*1.8f+i);
        glColor4f(1.f, 0.75f, 0.25f, 0.4f); glVertex2f(sx+cosf(ang)*sr/a, sy+sinf(ang)*sr);
        glColor4f(1.f, 0.4f, 0.f, 0.f);     glVertex2f(sx+cosf(ang+wid)*len/a, sy+sinf(ang+wid)*len);
                                            glVertex2f(sx+cosf(ang-wid)*len/a, sy+sinf(ang-wid)*len);
    } glEnd();
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    glColor4f(0.85f, 0.42f, 0.05f, 1.f); shape(GL_TRIANGLE_FAN, sx, sy, sr, sr, 60);
    glColor4f(1.f, 1.f, 0.9f, 1.f);      shape(GL_TRIANGLE_FAN, sx, sy, sr*0.8f, sr*0.8f, 60);

    // Earth
    glow(ex, ey, rz, 0.15f, 0.5f, 1.f, 3);
    glColor4f(0.04f, 0.15f, 0.50f, 1.f); shape(GL_TRIANGLE_FAN, ex, ey, rz, rz, 60);
    glColor4f(0.20f, 0.55f, 0.20f, 1.f);
    float conts[][4] = {{0.1f,-0.08f,0.22f,0.4f}, {0.42f,-0.12f,0.28f,0.34f}, {0.7f,-0.08f,0.24f,0.26f}, {0.64f,0.38f,0.18f,0.18f}, {0.14f,0.46f,0.52f,0.14f}};
    for(auto& c : conts) {
        float px = fmodf(c[0] + (t*0.06f)/(2.f*PI), 1.f); if(px < 0) px += 1.f;
        float wx = ex - rz/a + px*(rz*2.f/a), wy = ey + c[1]*rz, dx = (wx-ex)*a, dy = wy-ey;
        if(sqrtf(dx*dx+dy*dy) < rz*0.88f) shape(GL_TRIANGLE_FAN, wx, wy, c[2]*rz*0.5f, c[3]*rz*0.5f, 30);
    }
    glColor4f(0.88f, 0.93f, 1.f, 1.f);
    shape(GL_TRIANGLE_FAN, ex, ey-rz*0.76f, rz*0.48f, rz*0.2f, 30);
    shape(GL_TRIANGLE_FAN, ex, ey+rz*0.80f, rz*0.44f, rz*0.16f, 30);

    // Earth Shadow
    float sDir = atan2f(ey, ex-sx);
    glBegin(GL_TRIANGLE_FAN); glColor4f(0.f,0.02f,0.08f,0.8f); glVertex2f(ex+cosf(sDir+PI)*rz*0.22f/a, ey+sinf(sDir+PI)*rz*0.22f);
    for(int i=0; i<=40; i++) {
        float fd = i<4 ? i/4.f : i>36 ? (40-i)/4.f : 1.f;
        glColor4f(0.f,0.02f,0.08f,0.76f*fd);
        glVertex2f(ex+cosf(sDir+PI/2.f+PI*i/40)*rz*1.01f/a, ey+sinf(sDir+PI/2.f+PI*i/40)*rz*1.01f);
    } glEnd();

    // Moon
    glow(mx(), my(), mz, 0.75f, 0.78f, 0.9f, 3);
    glColor4f(0.48f, 0.48f, 0.55f, 1.f); shape(GL_TRIANGLE_FAN, mx(), my(), mz, mz, moonSides, t*0.05f);
    float mr[][4] = {{0.15f,0.05f,0.3f,0.26f},{-0.2f,-0.1f,0.22f,0.19f},{0.05f,-0.26f,0.18f,0.15f},{-0.1f,0.22f,0.15f,0.13f},{0.26f,-0.15f,0.12f,0.1f}};
    for(auto& m : mr) { glColor4f(0.28f,0.28f,0.35f,0.55f); shape(GL_TRIANGLE_FAN, mx()+m[0]*mz, my()+m[1]*mz, m[2]*mz, m[3]*mz, 20); }
    
    // Moon Shadow
    sDir = atan2f(my(), mx()-sx);
    glBegin(GL_TRIANGLE_FAN); glColor4f(0.f,0.01f,0.05f,0.88f); glVertex2f(mx()+cosf(sDir+PI)*mz*0.2f/a, my()+sinf(sDir+PI)*mz*0.2f);
    for(int i=0; i<=40; i++) {
        float fd = i<3 ? i/3.f : i>37 ? (40-i)/3.f : 1.f;
        glColor4f(0.f,0.01f,0.05f,0.84f*fd);
        glVertex2f(mx()+cosf(sDir+PI/2.f+PI*i/40)*mz*1.01f/a, my()+sinf(sDir+PI/2.f+PI*i/40)*mz*1.01f);
    } glEnd();
    glLineWidth(1.5f); glColor4f(0.85f,0.88f,1.f,0.35f); shape(GL_LINE_LOOP, mx(), my(), mz*1.01f, mz*1.01f, moonSides, t*0.05f);
}

// ─── Font & HUD ───────────────────────────────────────────────────────────
void drawChar(char c, float x, float y, float w, float h) {
    glBegin(GL_LINE_STRIP); w/=asp();
    if(c=='A'){ glVertex2f(x,y); glVertex2f(x,y+h); glVertex2f(x+w,y+h); glVertex2f(x+w,y); glEnd(); glBegin(GL_LINES); glVertex2f(x,y+h/2); glVertex2f(x+w,y+h/2); }
    if(c=='B'){ glVertex2f(x,y); glVertex2f(x,y+h); glVertex2f(x+w*0.8f,y+h); glVertex2f(x+w,y+h*0.75f); glVertex2f(x+w*0.8f,y+h/2); glVertex2f(x,y+h/2); glEnd(); glBegin(GL_LINE_STRIP); glVertex2f(x+w*0.8f,y+h/2); glVertex2f(x+w,y+h*0.25f); glVertex2f(x+w*0.8f,y); glVertex2f(x,y); }
    if(c=='C'){ glVertex2f(x+w,y); glVertex2f(x,y); glVertex2f(x,y+h); glVertex2f(x+w,y+h); }
    if(c=='E'){ glVertex2f(x+w,y); glVertex2f(x,y); glVertex2f(x,y+h); glVertex2f(x+w,y+h); glEnd(); glBegin(GL_LINES); glVertex2f(x,y+h/2); glVertex2f(x+w*0.8f,y+h/2); }
    if(c=='F'){ glVertex2f(x,y); glVertex2f(x,y+h); glVertex2f(x+w,y+h); glEnd(); glBegin(GL_LINES); glVertex2f(x,y+h/2); glVertex2f(x+w*0.8f,y+h/2); }
    if(c=='G'){ glVertex2f(x+w,y+h); glVertex2f(x,y+h); glVertex2f(x,y); glVertex2f(x+w,y); glVertex2f(x+w,y+h/2); glVertex2f(x+w/2,y+h/2); }
    if(c=='I'){ glVertex2f(x+w/2,y); glVertex2f(x+w/2,y+h); glEnd(); glBegin(GL_LINES); glVertex2f(x+w*0.2f,y); glVertex2f(x+w*0.8f,y); glVertex2f(x+w*0.2f,y+h); glVertex2f(x+w*0.8f,y+h); }
    if(c=='L'){ glVertex2f(x,y+h); glVertex2f(x,y); glVertex2f(x+w,y); }
    if(c=='M'){ glVertex2f(x,y); glVertex2f(x,y+h); glVertex2f(x+w/2,y+h/2); glVertex2f(x+w,y+h); glVertex2f(x+w,y); }
    if(c=='N'){ glVertex2f(x,y); glVertex2f(x,y+h); glVertex2f(x+w,y); glVertex2f(x+w,y+h); }
    if(c=='O'){ glVertex2f(x,y); glVertex2f(x,y+h); glVertex2f(x+w,y+h); glVertex2f(x+w,y); glVertex2f(x,y); }
    if(c=='Q'){ glVertex2f(x,y); glVertex2f(x,y+h); glVertex2f(x+w,y+h); glVertex2f(x+w,y); glVertex2f(x,y); glEnd(); glBegin(GL_LINES); glVertex2f(x+w/2,y+h/2); glVertex2f(x+w,y-h*0.2f); }
    if(c=='R'){ glVertex2f(x,y); glVertex2f(x,y+h); glVertex2f(x+w,y+h); glVertex2f(x+w,y+h/2); glVertex2f(x,y+h/2); glEnd(); glBegin(GL_LINES); glVertex2f(x+w/2,y+h/2); glVertex2f(x+w,y); }
    if(c=='S'){ glVertex2f(x,y); glVertex2f(x+w,y); glVertex2f(x+w,y+h/2); glVertex2f(x,y+h/2); glVertex2f(x,y+h); glVertex2f(x+w,y+h); }
    if(c=='T'){ glVertex2f(x+w/2,y); glVertex2f(x+w/2,y+h); glEnd(); glBegin(GL_LINES); glVertex2f(x,y+h); glVertex2f(x+w,y+h); }
    if(c=='U'){ glVertex2f(x,y+h); glVertex2f(x,y); glVertex2f(x+w,y); glVertex2f(x+w,y+h); }
    if(c=='W'){ glVertex2f(x,y+h); glVertex2f(x,y); glVertex2f(x+w/2,y+h/2); glVertex2f(x+w,y); glVertex2f(x+w,y+h); }
    if(c=='X'){ glVertex2f(x,y); glVertex2f(x+w,y+h); glEnd(); glBegin(GL_LINES); glVertex2f(x,y+h); glVertex2f(x+w,y); }
    glEnd();
}

void drawHUD() {
    float a = asp(), elo = fmodf(moonAngle, 2.f*PI); if(elo < 0) elo += 2.f*PI;
    float pR = 1.f - 0.06f/a, pL = pR - 0.42f/a, pT = 1.f - 0.02f, pB = pT - 0.52f, cx = (pL+pR)*0.5f, cy = pT - 0.22f, r = 0.1f;
    
    glColor4f(0.04f, 0.02f, 0.12f, 0.82f); glBegin(GL_QUADS); glVertex2f(pL,pB); glVertex2f(pR,pB); glVertex2f(pR,pT); glVertex2f(pL,pT); glEnd();

    bool wax = elo <= PI, cres = cosf(elo) > 0.f;
    glColor4f(0.06f, 0.05f, 0.12f, 1.f); shape(GL_TRIANGLE_FAN, cx, cy, r, r, 50); // Dark Base
    
    glColor4f(0.82f, 0.84f, 0.92f, 1.f); glBegin(GL_TRIANGLE_FAN); glVertex2f(cx,cy); // Bright Half
    for(int i=0; i<=50; i++) { float ang = (wax ? -PI/2.f : PI/2.f) + PI*i/50.f; glVertex2f(cx+cosf(ang)*r/a, cy+sinf(ang)*r); } glEnd();
    
    glColor4f(cres?0.06f:0.82f, cres?0.05f:0.84f, cres?0.12f:0.92f, 1.f); // Terminator
    float w = r * fabsf(cosf(elo)); glBegin(GL_TRIANGLE_FAN); glVertex2f(cx,cy);
    for(int i=0; i<=50; i++) { float ang = -PI/2.f + PI*i/50.f, nx = cosf(ang)*w; glVertex2f(cx + (wax!=cres ? -nx : nx)/a, cy + sinf(ang)*r); } glEnd();
    
    glColor4f(0.6f, 0.65f, 0.9f, 0.6f); shape(GL_LINE_LOOP, cx, cy, r, r, 60); // Outline

    // Text Label
    float p = elo/(2.f*PI);
    const char* nm = (p<0.03||p>=0.97)?"NEW MOON" : (p<0.22)?"WAXING CRESCENT" : (p<0.28)?"FIRST QUARTER" : (p<0.47)?"WAXING GIBBOUS" : (p<0.53)?"FULL MOON" : (p<0.72)?"WANING GIBBOUS" : (p<0.78)?"LAST QUARTER" : "WANING CRESCENT";
    glLineWidth(1.8f); glColor4f(0.85f, 0.88f, 0.95f, 0.9f);
    int len=0; while(nm[len]!='\0') len++;
    float fs = 0.035f, tx = cx - (len*(fs*1.1f)*0.5f/a) + (fs*0.1f/a);
    for(int i=0; i<len; i++) { if(nm[i]!=' ') drawChar(nm[i], tx, pB+0.08f, fs*0.6f, fs); tx += (fs*1.1f)/a; }
}

// ─── Input & Main ─────────────────────────────────────────────────────────
void input(GLFWwindow* w, double xp, double yp) {
    if(!dragging) return;
    float nx = ((xp/winW)*2.f-1.f)*asp(), ny = -((yp/winH)*2.f-1.f);
    moonAngle = atan2f(ny, nx);
}
void mouse(GLFWwindow* w, int b, int act, int) {
    if(b==0 && act==1) { double x,y; glfwGetCursorPos(w,&x,&y); float nx=((x/winW)*2.f-1.f)*asp(), ny=-((y/winH)*2.f-1.f), dx=nx-mx()*asp(), dy=ny-my(); dragging=(dx*dx+dy*dy < 0.02f*zoom); } else dragging=false;
}

int main() {
    glfwInit(); glfwWindowHint(GLFW_SAMPLES, 4);
    GLFWwindow* win = glfwCreateWindow(winW, winH, "Solar System (Optimized)", 0, 0);
    glfwMakeContextCurrent(win); gladLoadGL();
    glfwSetCursorPosCallback(win, input); glfwSetMouseButtonCallback(win, mouse);
    glfwSetScrollCallback(win, [](GLFWwindow*, double, double y){ zoom=fmaxf(0.3f, fminf((SUN_X-0.15f)/orbitRadius, zoom*(y>0?1.08f:0.93f))); });
    glfwSetKeyCallback(win, [](GLFWwindow*, int k, int, int a, int){ if(a) { if(k==32) paused=!paused; if(k==61||k==334) speedMult=fminf(speedMult+.25f, 8.f); if(k==45||k==333) speedMult=fmaxf(speedMult-.25f, 0.1f); if(k==91) moonSides=fmaxf(3,moonSides-1); if(k==93) moonSides=fminf(20,moonSides+1); }});
    glfwSetFramebufferSizeCallback(win, [](GLFWwindow*, int w, int h){ winW=w; winH=h; glViewport(0,0,w,h); });

    glEnable(GL_BLEND); glEnable(GL_POINT_SMOOTH); glEnable(GL_LINE_SMOOTH); glEnable(GL_MULTISAMPLE);
    for(auto& s : stars) { s.x=rng()*2.f-1.f; s.y=rng()*2.f-1.f; s.r=rng()<0.6f?rng()*0.003f+0.001f:rng()*0.007f+0.003f; s.bri=0.3f+rng()*0.7f; s.spd=0.5f+rng()*3.f; s.ph=rng()*PI*2.f; int tp=(int)(rng()*4.f)%4; s.cr=tp==0?0.6f:1.f; s.cg=tp==0?0.75f:tp==1?0.9f:tp==2?0.65f:1.f; s.cb=tp==0?1.f:tp==1?0.7f:tp==2?0.4f:1.f; }

    double prev = glfwGetTime();
    while(!glfwWindowShouldClose(win)) {
        double now = glfwGetTime(); float dt = fminf(now-prev, 0.05f); prev = now;
        if(!paused) { t += dt; if(!dragging) moonAngle = fmodf(moonAngle + 0.3f*dt*speedMult, 2.f*PI); }
        
        glClear(GL_COLOR_BUFFER_BIT);
        drawWorld(SUN_X*zoom, 0.f, 0.f, 0.f, asp(), 0.085f*zoom, 0.055f*zoom);
        drawHUD();
        glfwSwapBuffers(win); glfwPollEvents();
    }
    glfwTerminate(); return 0;
}
