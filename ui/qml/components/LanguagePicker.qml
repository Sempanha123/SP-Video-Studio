import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Phase22 1.0
import "../theme"
ColumnLayout {
    id: root
    property string currentCode: "en"
    property string engineId: ""
    property string capability: "all"
    property string sourceCode: ""
    signal codeSelected(string code)
    spacing: Theme.spacing.xs
    function supportLabel(value) {
        var v=String(value||"").toLowerCase()
        if(v.indexOf("unsupported")>=0||v==="none") return "Unsupported"
        if(v.indexOf("model")>=0||v.indexOf("required")>=0) return "Model Required"
        if(v.indexOf("partial")>=0||v.indexOf("fallback")>=0||v.indexOf("limited")>=0) return "Partially Supported"
        return "Supported"
    }
    function supportStatus(value) {
        var label=supportLabel(value)
        if(label==="Unsupported")return "neutral"
        if(label==="Model Required"||label==="Partially Supported")return "warning"
        return "ready"
    }
    SearchField { id: search; Layout.fillWidth: true; accessibleName:"Search languages"; placeholderText: "Search language"; onTextChanged: combo.model = LanguageCatalog.search(text); onClearRequested: combo.model = LanguageCatalog.languages }
    AppComboBox {
        id: combo; Layout.fillWidth: true; model: LanguageCatalog.languages; textRole: "nativeName"; accessibleName:"Language"
        Component.onCompleted: selectCode(root.currentCode)
        onActivated: { if(currentIndex<0||!model||currentIndex>=model.length)return; root.currentCode=model[currentIndex].code; root.codeSelected(root.currentCode) }
        function selectCode(code){for(var i=0;model&&i<model.length;++i)if(model[i].code===code){currentIndex=i;return}}
        contentItem: RowLayout {
            spacing: Theme.spacing.sm
            ColumnLayout { Layout.fillWidth:true; spacing:0
                Text { Layout.fillWidth:true; text: combo.currentIndex>=0&&combo.model&&combo.currentIndex<combo.model.length ? combo.model[combo.currentIndex].nativeName : "Choose language"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.bodySmall; font.weight:Theme.type.medium; elide:Text.ElideRight; lineHeightMode:Text.ProportionalHeight; lineHeight:Theme.type.multilingualLineHeight }
                Text { Layout.fillWidth:true; text: combo.currentIndex>=0&&combo.model&&combo.currentIndex<combo.model.length ? combo.model[combo.currentIndex].displayName : ""; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption; elide:Text.ElideRight }
            }
        }
    }
    Flow { Layout.fillWidth:true; spacing:4; visible:combo.currentIndex>=0&&combo.model&&combo.currentIndex<combo.model.length
        StatusBadge { text: visible ? "STT · "+root.supportLabel(combo.model[combo.currentIndex].sttSupport) : ""; status: visible?root.supportStatus(combo.model[combo.currentIndex].sttSupport):"neutral" }
        StatusBadge { text: visible ? "TTS · "+root.supportLabel(combo.model[combo.currentIndex].ttsSupport) : ""; status: visible?root.supportStatus(combo.model[combo.currentIndex].ttsSupport):"neutral" }
        StatusBadge { text: visible ? "Translate · "+root.supportLabel(combo.model[combo.currentIndex].translationSupport) : ""; status: visible?root.supportStatus(combo.model[combo.currentIndex].translationSupport):"neutral" }
    }
}
