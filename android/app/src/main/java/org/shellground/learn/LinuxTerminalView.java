package org.shellground.learn;

import android.content.Context;
import android.graphics.*;
import android.text.InputType;
import android.view.*;
import android.view.inputmethod.*;
import org.json.*;
import java.util.*;

/** Native cell renderer/input surface. ANSI interpretation is handled by pyte;
 * all shell/editor behavior belongs to the real guest, never to this View.
 */
public final class LinuxTerminalView extends View {
    public interface Actions {void input(String text);void resize(int columns,int rows);void scroll(int delta);void copy();}
    private final Actions actions;
    private final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);
    private JSONObject frame;
    private float cellWidth,cellHeight,baseline,downY,lastY;
    private boolean dragged;
    private int columns=80,rows=24;
    private static final Map<String,Integer> COLORS=new HashMap<>();
    static{
        String[] names={"black","red","green","brown","blue","magenta","cyan","white","brightblack","brightred","brightgreen","brightbrown","brightblue","brightmagenta","brightcyan","brightwhite"};
        int[] values={0xff17201c,0xfff08080,0xff8acf98,0xffdcc58b,0xff82aaff,0xffc9a0dc,0xff82d8d8,0xffe4e9e5,0xff778580,0xffff9797,0xffa6efb4,0xffffdf9f,0xffa8c8ff,0xffe5bcfa,0xffa9ffff,0xffffffff};
        for(int i=0;i<names.length;i++)COLORS.put(names[i],values[i]);
    }
    public LinuxTerminalView(Context context,Actions actions){
        super(context);this.actions=actions;setFocusable(true);setFocusableInTouchMode(true);
        setBackgroundColor(0xff101b20);setContentDescription("실제 Linux 터미널");setTag("linux-terminal");
        paint.setTypeface(Typeface.MONOSPACE);paint.setTextSize(13*getResources().getDisplayMetrics().scaledDensity);
        cellWidth=paint.measureText("M");Paint.FontMetrics fm=paint.getFontMetrics();cellHeight=(float)Math.ceil(fm.descent-fm.ascent+2);baseline=-fm.ascent;
        setOnLongClickListener(v->{actions.copy();return true;});
    }
    public void display(JSONObject next){frame=next;invalidate();}
    public int columns(){return columns;}
    public int rows(){return rows;}
    @Override protected void onSizeChanged(int w,int h,int oldw,int oldh){
        columns=Math.max(10,Math.min(160,(int)((w-12)/cellWidth)));
        rows=Math.max(4,Math.min(60,(int)((h-12)/cellHeight)));
        actions.resize(columns,rows);
    }
    private int color(String value,boolean background){
        if(COLORS.containsKey(value))return COLORS.get(value);
        if(value.matches("[0-9a-fA-F]{6}"))return Color.parseColor("#"+value);
        return background?0xff101b20:0xffdce6de;
    }
    @Override protected void onDraw(Canvas canvas){
        super.onDraw(canvas);if(frame==null)return;
        try{
            JSONArray lines=frame.getJSONArray("rows");
            for(int y=0;y<Math.min(rows,lines.length());y++){
                JSONArray cells=lines.getJSONArray(y);
                for(int i=0;i<cells.length();i++){
                    JSONArray cell=cells.getJSONArray(i);int x=cell.getInt(0);String text=cell.getString(1);
                    int fg=color(cell.getString(2),false),bg=color(cell.getString(3),true);
                    if(cell.getBoolean(5)){int swap=fg;fg=bg;bg=swap;}
                    int next=i+1<cells.length()?cells.getJSONArray(i+1).getInt(0):x+1;
                    paint.setColor(bg);canvas.drawRect(6+x*cellWidth,6+y*cellHeight,6+next*cellWidth,6+(y+1)*cellHeight,paint);
                    paint.setColor(fg);paint.setFakeBoldText(cell.getBoolean(4));paint.setUnderlineText(cell.getBoolean(6));
                    canvas.drawText(text,6+x*cellWidth,6+y*cellHeight+baseline,paint);
                }
            }
            paint.setFakeBoldText(false);paint.setUnderlineText(false);
            JSONArray cursor=frame.getJSONArray("cursor");
            if(cursor.getBoolean(2)&&hasFocus()){
                paint.setColor(0xff8acf98);paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(2);
                canvas.drawRect(6+cursor.getInt(0)*cellWidth,6+cursor.getInt(1)*cellHeight,6+(cursor.getInt(0)+1)*cellWidth,6+(cursor.getInt(1)+1)*cellHeight,paint);
                paint.setStyle(Paint.Style.FILL);
            }
        }catch(JSONException ignored){}
    }
    @Override public boolean onCheckIsTextEditor(){return true;}
    @Override public InputConnection onCreateInputConnection(EditorInfo out){
        out.inputType=InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS|InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD;
        out.imeOptions=EditorInfo.IME_FLAG_NO_EXTRACT_UI|EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING|EditorInfo.IME_ACTION_NONE;
        return new BaseInputConnection(this,false){
            @Override public boolean commitText(CharSequence text,int cursor){actions.input(text.toString());return true;}
            @Override public boolean deleteSurroundingText(int before,int after){
                StringBuilder keys=new StringBuilder();for(int i=0;i<Math.min(100,Math.max(0,before));i++)keys.append('\u007f');
                actions.input(keys.toString());return true;
            }
            @Override public boolean sendKeyEvent(KeyEvent event){return event.getAction()!=KeyEvent.ACTION_DOWN||onKeyDown(event.getKeyCode(),event);}
        };
    }
    @Override public boolean onKeyDown(int code,KeyEvent event){
        String keys=switch(code){
            case KeyEvent.KEYCODE_ENTER -> "\r";case KeyEvent.KEYCODE_DEL -> "\u007f";
            case KeyEvent.KEYCODE_FORWARD_DEL -> "\u001b[3~";case KeyEvent.KEYCODE_TAB -> "\t";
            case KeyEvent.KEYCODE_ESCAPE -> "\u001b";case KeyEvent.KEYCODE_DPAD_UP -> "\u001b[A";
            case KeyEvent.KEYCODE_DPAD_DOWN -> "\u001b[B";case KeyEvent.KEYCODE_DPAD_RIGHT -> "\u001b[C";
            case KeyEvent.KEYCODE_DPAD_LEFT -> "\u001b[D";default -> null;
        };
        if(keys==null){int unicode=event.getUnicodeChar(event.getMetaState()&~KeyEvent.META_CTRL_MASK);
            if(event.isCtrlPressed()&&unicode>=64&&unicode<128)keys=String.valueOf((char)(unicode&31));
            else if(unicode!=0)keys=new String(Character.toChars(unicode));}
        if(keys==null)return super.onKeyDown(code,event);actions.input(keys);return true;
    }
    @Override public boolean onTouchEvent(android.view.MotionEvent event){
        if(event.getAction()==MotionEvent.ACTION_DOWN){downY=lastY=event.getY();dragged=false;super.onTouchEvent(event);return true;}
        if(event.getAction()==MotionEvent.ACTION_MOVE){
            if(Math.abs(event.getY()-downY)>cellHeight)dragged=true;
            int delta=(int)((lastY-event.getY())/cellHeight);
            if(dragged&&delta!=0){cancelLongPress();actions.scroll(delta);lastY=event.getY();}return true;
        }
        if(event.getAction()==MotionEvent.ACTION_UP){
            if(!dragged){performClick();requestFocus();((InputMethodManager)getContext().getSystemService(Context.INPUT_METHOD_SERVICE)).showSoftInput(this,InputMethodManager.SHOW_IMPLICIT);}
            super.onTouchEvent(event);return true;
        }
        return super.onTouchEvent(event);
    }
    @Override public boolean performClick(){super.performClick();return true;}
}
