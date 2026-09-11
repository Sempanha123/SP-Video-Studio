import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Phase22 1.0
import "../theme"
import "../components"

AppDialog {
    id: root
    property var controller: null
    width: 600
    parent: Overlay.overlay
    x: parent ? (parent.width-width)/2 : 0
    y: parent ? (parent.height-height)/2 : 0
    header: null; footer: null
    property var selectedSource: sourceCombo.currentIndex>=0 && controller && controller.sources.length>sourceCombo.currentIndex ? controller.sources[sourceCombo.currentIndex] : ({})
    property string targetCode: "km"
    contentItem: ColumnLayout {
        spacing:Theme.spacing.lg
        Text { text:"New Translation"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.heading; font.weight:Theme.type.semibold }
        Text { Layout.fillWidth:true; text:"Choose a content language and provider-supported target. App language and content language remain separate."; color:Theme.colors.textSecondary; font.family:Theme.type.family; font.pixelSize:Theme.type.bodySmall; wrapMode:Text.WordWrap }
        GridLayout { Layout.fillWidth:true; columns:2; columnSpacing:Theme.spacing.lg; rowSpacing:Theme.spacing.md
            Text { text:"Source"; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
            AppComboBox { id:sourceCombo; Layout.fillWidth:true; model:root.controller?root.controller.sources:[]; textRole:"name" }
            Text { text:"Target"; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
            LanguagePicker { id:targetPicker; Layout.fillWidth:true; currentCode: root.selectedSource.language==="km"?"en":"km"; onCodeSelected:function(code){root.targetCode=code} }
            Text { text:"Provider"; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
            AppComboBox { id:providerCombo; Layout.fillWidth:true; model:root.controller?root.controller.providers:[]; textRole:"name" }
            Text { text:"Device"; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
            AppComboBox { id:deviceCombo; Layout.fillWidth:true; model:["Auto","CPU","CUDA"] }
            Text { text:"Keep Terms"; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
            AppTextField { id:keepTerms; Layout.fillWidth:true; placeholderText:"OpenAI, VoxCPM2, product names…" }
        }
        InfoBanner { Layout.fillWidth:true; variant:"warning"; text: providerCombo.currentIndex>=0 && root.selectedSource.language && !LanguageCatalog.supportsTranslation(root.selectedSource.language,root.targetCode,["local-marian","manual"][providerCombo.currentIndex]) ? "This language pair is not supported by the selected provider/model. Choose another provider or install a model." : "Review names, numbers and quotes before publishing." }
        RowLayout { Layout.fillWidth:true; Item { Layout.fillWidth:true }; SecondaryButton { text:"Cancel"; onClicked:root.close() }
            AppButton { text:"Translate"; enabled:root.controller&&sourceCombo.currentIndex>=0; onClicked:{ var source=root.selectedSource; var providers=["local-marian","manual"]; var devices=["auto","cpu","cuda"]; if(root.controller.createTranslation(source.type||"",source.id||"",root.targetCode,providers[providerCombo.currentIndex],devices[deviceCombo.currentIndex],keepTerms.text))root.close() } }
        }
    }
}
