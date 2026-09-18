package org.shellground.learn;

import android.content.Context;
import android.text.InputType;
import android.view.View;
import android.widget.*;
import org.json.*;
import java.util.LinkedHashMap;
import java.util.Map;

/** Native answer fields: blank booleans remain unanswered; no expected values. */
final class CondaAnswerForm extends LinearLayout {
    private final Map<String,View> fields=new LinkedHashMap<>();
    CondaAnswerForm(Context context){super(context);setOrientation(VERTICAL);int pad=Math.round(16*getResources().getDisplayMetrics().density);setPadding(pad,0,pad,pad);}
    void show(JSONArray schema)throws JSONException{
        removeAllViews();fields.clear();setVisibility(schema.length()==0?GONE:VISIBLE);
        for(int i=0;i<schema.length();i++){
            JSONObject field=schema.getJSONObject(i);String key=field.getString("key");
            TextView label=new TextView(getContext());label.setText(field.getString("label"));label.setTextSize(14);label.setTextColor(0xff202b33);addView(label);
            View input;
            if(field.getString("input").equals("boolean")){
                Spinner select=new Spinner(getContext());select.setAdapter(new ArrayAdapter<>(getContext(),android.R.layout.simple_spinner_dropdown_item,new String[]{"선택하세요","예","아니오"}));input=select;
            }else{
                EditText edit=new EditText(getContext());edit.setTextColor(0xff202b33);edit.setTextSize(14);
                edit.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS);edit.setSingleLine(true);input=edit;
            }
            input.setContentDescription(field.getString("label"));input.setTag("conda-answer-"+key);
            input.setMinimumHeight(Math.round(48*getResources().getDisplayMetrics().density));addView(input,new LayoutParams(-1,-2));fields.put(key,input);
        }
    }
    JSONObject answers()throws JSONException{
        JSONObject result=new JSONObject();
        for(Map.Entry<String,View> entry:fields.entrySet()){
            View input=entry.getValue();
            if(input instanceof Spinner){int selected=((Spinner)input).getSelectedItemPosition();if(selected>0)result.put(entry.getKey(),selected==1);}
            else {String value=((EditText)input).getText().toString();if(!value.isEmpty())result.put(entry.getKey(),value);}
        }
        return result;
    }
}
