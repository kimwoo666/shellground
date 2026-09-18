package org.shellground.learn;

import android.app.AlertDialog;
import android.content.Context;
import android.graphics.Typeface;
import android.text.*;
import android.view.*;
import android.widget.*;
import org.json.*;
import java.util.*;

/** Native cell document. Execution belongs to the guest, never this view. */
final class NotebookEditor extends LinearLayout {
    interface Actions { void perform(String operation,JSONObject arguments); void interrupt(); void changed(); }
    private final Actions actions;
    private final LinearLayout document;
    private final Button kernel;
    private final List<Button> buttons=new ArrayList<>();
    private final Map<String,TextView> outputs=new HashMap<>();
    private final Map<String,EditText> editors=new HashMap<>();
    private JSONArray cells=new JSONArray(),kernels=new JSONArray();
    private String selected="",selectedKernel="";
    private boolean enabled;
    NotebookEditor(Context context,Actions actions){
        super(context);this.actions=actions;setOrientation(VERTICAL);setBackgroundColor(0xfff3f6f5);
        HorizontalScrollView tools=new HorizontalScrollView(context);LinearLayout bar=row();tools.addView(bar);addView(tools);
        kernel=button("커널 선택",this::pickKernel);bar.addView(kernel);
        bar.addView(button("셀 실행",this::runSelected));
        bar.addView(button("모두 실행",()->perform("run_all",object("cells",snapshot()))));
        Button interrupt=button("중단",actions::interrupt);buttons.remove(interrupt);bar.addView(interrupt);
        bar.addView(button("저장",this::save));bar.addView(button("재시작",()->new AlertDialog.Builder(getContext())
            .setMessage("커널 변수와 실행 상태를 초기화할까요? 셀 코드는 유지됩니다.")
            .setPositiveButton("재시작",(d,n)->perform("restart",new JSONObject())).setNegativeButton("취소",null).show()));
        bar.addView(button("+ 코드",()->addCell("code")));bar.addView(button("+ 메모",()->addCell("markdown")));
        ScrollView scroll=new ScrollView(context);document=new LinearLayout(context);document.setOrientation(VERTICAL);
        document.setPadding(dp(10),dp(8),dp(10),dp(16));scroll.addView(document);addView(scroll,new LayoutParams(-1,0,1));
    }
    private int dp(int n){return Math.round(n*getResources().getDisplayMetrics().density);}
    private LinearLayout row(){LinearLayout view=new LinearLayout(getContext());view.setOrientation(HORIZONTAL);return view;}
    private Button button(String label,Runnable action){Button b=new Button(getContext());b.setText(label);b.setTextSize(12);b.setAllCaps(false);
        b.setMinWidth(dp(64));b.setMinimumHeight(dp(48));b.setOnClickListener(v->action.run());buttons.add(b);return b;}
    private JSONObject object(String key,Object value){try{return new JSONObject().put(key,value);}catch(JSONException e){throw new IllegalArgumentException(e);}}
    JSONArray snapshot(){try{return new JSONArray(cells.toString());}catch(JSONException e){throw new IllegalStateException(e);}}
    void load(JSONArray source){try{cells=new JSONArray(source.toString());selected=cells.length()>0?cells.getJSONObject(0).getString("id"):"";outputs.clear();render();}catch(JSONException e){throw new IllegalArgumentException(e);}}
    void available(boolean available){enabled=available;for(Button b:buttons)b.setEnabled(available);for(EditText e:editors.values())e.setEnabled(available);}
    void kernels(JSONArray values){kernels=values;}
    void identity(JSONObject value){
        String name=value.optString("kernel",value.optString("selected",selectedKernel));
        if(!name.isEmpty())selectedKernel=name;
        JSONObject actual=value.optJSONObject("values");
        kernel.setText(selectedKernel.isEmpty()?"커널 선택":selectedKernel);
        if(actual!=null)kernel.setContentDescription(selectedKernel+" · "+actual.optString("executable")+" · "+actual.optString("prefix"));
    }
    private void pickKernel(){
        String[] labels=new String[kernels.length()+1];
        for(int i=0;i<kernels.length();i++){JSONObject k=kernels.optJSONObject(i);labels[i]=k.optString("display_name")+" ["+k.optString("name")+"]\n"+k.optString("executable");}
        labels[kernels.length()]="목록 새로 고침";
        new AlertDialog.Builder(getContext()).setTitle("실행할 Python 커널").setItems(labels,(d,n)->{
            if(n==kernels.length())perform("list",new JSONObject());else perform("select",object("name",kernels.optJSONObject(n).optString("name")));
        }).show();
    }
    private void perform(String operation,JSONObject arguments){if(enabled)actions.perform(operation,arguments);}
    private JSONObject selectedCell(){for(int i=0;i<cells.length();i++)if(cells.optJSONObject(i).optString("id").equals(selected))return cells.optJSONObject(i);return null;}
    private void runSelected(){JSONObject cell=selectedCell();if(cell==null)return;
        if(!cell.optString("type").equals("code")){Toast.makeText(getContext(),"메모 셀은 설명이며 Python으로 실행하지 않습니다.",Toast.LENGTH_SHORT).show();return;}
        try{perform("execute",new JSONObject().put("cell_id",selected).put("code",cell.getString("source")));}catch(JSONException ignored){}}
    private void addCell(String type){if(cells.length()>=32){Toast.makeText(getContext(),"문서당 최대 32개 셀입니다.",Toast.LENGTH_SHORT).show();return;}
        try{String id="cell-"+UUID.randomUUID();cells.put(new JSONObject().put("id",id).put("type",type).put("source",""));selected=id;render();actions.changed();}
        catch(JSONException ignored){}
    }
    private void move(int index,int direction){int target=index+direction;if(target<0||target>=cells.length())return;
        try{JSONObject a=cells.getJSONObject(index),b=cells.getJSONObject(target);cells.put(index,b);cells.put(target,a);render();actions.changed();}catch(JSONException ignored){}}
    private void remove(int index){cells.remove(index);render();actions.changed();}
    private void render(){
        document.removeAllViews();editors.clear();
        // Remove controls belonging to the previous document; toolbar remains.
        buttons.removeIf(b->b.getTag()!=null&&"cell-control".equals(b.getTag()));
        for(int i=0;i<cells.length();i++){
            final int at=i;JSONObject cell=cells.optJSONObject(i);String id=cell.optString("id");
            LinearLayout card=new LinearLayout(getContext());card.setOrientation(VERTICAL);card.setPadding(dp(8),dp(4),dp(8),dp(8));card.setBackgroundColor(0xffffffff);
            LayoutParams cardParams=new LayoutParams(-1,-2);cardParams.bottomMargin=dp(10);document.addView(card,cardParams);
            LinearLayout heading=row();TextView label=new TextView(getContext());label.setText((i+1)+" · "+(cell.optString("type").equals("code")?"코드":"Markdown 메모"));label.setTextColor(0xff16725d);label.setGravity(Gravity.CENTER_VERTICAL);
            heading.addView(label,new LayoutParams(0,dp(48),1));
            Button up=button("↑",()->move(at,-1)),down=button("↓",()->move(at,1)),remove=button("삭제",()->remove(at));
            for(Button b:new Button[]{up,down,remove}){b.setTag("cell-control");heading.addView(b,new LayoutParams(dp(56),dp(48)));}card.addView(heading);
            EditText edit=new EditText(getContext());edit.setTextSize(14);edit.setTypeface(Typeface.MONOSPACE);edit.setTextColor(0xffe0ede7);edit.setBackgroundColor(0xff101b20);
            edit.setPadding(dp(10),dp(10),dp(10),dp(10));edit.setGravity(Gravity.TOP|Gravity.START);edit.setMinLines(3);edit.setMaxLines(18);
            edit.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_FLAG_MULTI_LINE|android.text.InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS);
            edit.setHorizontallyScrolling(true);edit.setText(cell.optString("source"));edit.setContentDescription("셀 "+(i+1));
            edit.setOnFocusChangeListener((v,focus)->{if(focus)selected=id;});
            edit.setOnKeyListener((v,key,event)->{if(key==KeyEvent.KEYCODE_ENTER&&event.isShiftPressed()){
                if(event.getAction()==KeyEvent.ACTION_DOWN&&event.getRepeatCount()==0){selected=id;runSelected();}return true;}return false;});
            edit.addTextChangedListener(new TextWatcher(){public void beforeTextChanged(CharSequence s,int st,int count,int after){}public void onTextChanged(CharSequence s,int st,int before,int count){
                try{cell.put("source",s.toString());actions.changed();}catch(JSONException ignored){}}public void afterTextChanged(Editable e){}});
            editors.put(id,edit);card.addView(edit,new LayoutParams(-1,-2));
            TextView output=outputs.get(id);if(output==null){output=new TextView(getContext());outputs.put(id,output);output.setTextIsSelectable(true);output.setTypeface(Typeface.MONOSPACE);output.setTextSize(13);output.setTextColor(0xff253b34);output.setPadding(dp(8),dp(8),dp(8),dp(8));}
            if(output.getParent()!=null)((ViewGroup)output.getParent()).removeView(output);card.addView(output);
        }
        available(enabled);
    }
    void result(String operation,JSONObject result)throws JSONException{
        if(result.has("kernels"))kernels(result.getJSONArray("kernels"));
        identity(result);
        if(result.has("batch")){JSONArray batch=result.getJSONArray("batch");for(int i=0;i<batch.length();i++){JSONObject entry=batch.getJSONObject(i);showOutput(entry.getString("cell_id"),entry.getJSONObject("result"));}}
        else if(operation.equals("execute"))showOutput(result.optString("cell_id",selected),result);
        else if(operation.equals("save"))Toast.makeText(getContext(),"노트북 파일을 실습 폴더에 저장했습니다.",Toast.LENGTH_SHORT).show();
        else if(operation.equals("restart"))Toast.makeText(getContext(),"커널 변수를 초기화했습니다. 셀 코드는 유지됩니다.",Toast.LENGTH_SHORT).show();
    }
    private void showOutput(String id,JSONObject result)throws JSONException{
        StringBuilder text=new StringBuilder("실행 ["+result.opt("execution_count")+"]\n");JSONArray messages=result.optJSONArray("messages");
        if(messages!=null)for(int i=0;i<messages.length();i++){
            JSONObject message=messages.getJSONObject(i),content=message.getJSONObject("content");String type=message.getString("type");
            if(type.equals("stream"))text.append(content.optString("text"));
            else if(type.equals("error"))text.append(content.optString("ename")).append(": ").append(content.optString("evalue")).append('\n');
            else if(content.has("data"))text.append(content.getJSONObject("data").optString("text/plain")).append('\n');
        }
        if(result.optBoolean("truncated"))text.append("\n출력이 길어 일부만 표시됩니다.");
        TextView output=outputs.get(id);if(output!=null)output.setText(text);
    }
    private void save(){EditText filename=new EditText(getContext());filename.setSingleLine(true);filename.setText("report.ipynb");
        new AlertDialog.Builder(getContext()).setTitle("노트북 파일 저장").setView(filename).setPositiveButton("저장",(d,n)->{
            try{perform("save",new JSONObject().put("filename",filename.getText().toString()).put("cells",snapshot()));}catch(JSONException ignored){}
        }).setNegativeButton("취소",null).show();}
}
