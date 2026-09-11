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
    SearchField { id: search; Layout.fillWidth: true; placeholderText: "Search language"; onTextChanged: combo.model = LanguageCatalog.search(text); onClearRequested: combo.model = LanguageCatalog.languages }
    AppComboBox {
        id: combo; Layout.fillWidth: true; model: LanguageCatalog.languages; textRole: "nativeName"
        Component.onCompleted: selectCode(root.currentCode)
        onActivated: { if(currentIndex<0||!model||currentIndex>=model.length)return; root.currentCode=model[currentIndex].code; root.codeSelected(root.currentCode) }
        function selectCode(code){for(var i=0;model&&i<model.length;++i)if(model[i].code===code){currentIndex=i;return}}
        contentItem: RowLayout {
            spacing: Theme.spacing.sm
            ColumnLayout { Layout.fillWidth:true; spacing:0
                Text { Layout.fillWidth:true; text: combo.currentIndex>=0&&combo.model&&combo.currentIndex<combo.model.length ? combo.model[combo.currentIndex].nativeName : "Choose language"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.bodySmall; font.weight:Theme.type.medium; elide:Text.ElideRight }
                Text { Layout.fillWidth:true; text: combo.currentIndex>=0&&combo.model&&combo.currentIndex<combo.model.length ? combo.model[combo.currentIndex].displayName : ""; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption; elide:Text.ElideRight }
            }
        }
    }
    Flow { Layout.fillWidth:true; spacing:4; visible:combo.currentIndex>=0&&combo.model&&combo.currentIndex<combo.model.length
        StatusBadge { text: visible ? "STT · "+combo.model[combo.currentIndex].sttSupport.replaceAll("_"," ") : ""; status: text.indexOf("unsupported")>=0?"neutral":"ready" }
        StatusBadge { text: visible ? "TTS · "+combo.model[combo.currentIndex].ttsSupport.replaceAll("_"," ") : ""; status: text.indexOf("unsupported")>=0?"neutral":"ready" }
        StatusBadge { text: visible ? "Translate · "+combo.model[combo.currentIndex].translationSupport.replaceAll("_"," ") : ""; status: text.indexOf("unsupported")>=0?"neutral":"ready" }
    }
}
